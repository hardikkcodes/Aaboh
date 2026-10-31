"""Daily decision support built from stored forecasts, alerts and resident reports.

Everything here is a transparent rule over stored records. Heat index is calculated
from forecast temperature and humidity, so it is labelled as derived guidance, not
a measurement. Advice never says that a place or road is safe.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from statistics import mean
from zoneinfo import ZoneInfo

from django.utils import timezone

from apps.air_quality.models import AirForecastHour
from apps.core.geometry import haversine_m
from apps.core.quality import DataState, freshness_state
from apps.incidents.services import live_reports
from apps.locations.models import Area, Neighbourhood
from apps.weather.conditions import condition_for_code
from apps.weather.models import DailyModelForecast
from apps.weather.selectors import hourly_records, latest_retrieved_at

from .place_status import _air_quality_section, _alerts_section, _center

IST = ZoneInfo("Asia/Kolkata")
FORECAST_MAX_AGE = timedelta(hours=3)
RAIN_SOON_HOURS = 2
RAIN_LIKELY_PROBABILITY = 50
RAIN_LIKELY_MM = 0.5
HEAVY_RAIN_SOON_MM = 10.0
OUTDOOR_MAX_RAIN_PROBABILITY = 40
OUTDOOR_FIRST_HOUR = 5
OUTDOOR_LAST_HOUR = 21
NIGHT_HOURS = {22, 23, 0, 1, 2, 3, 4, 5}
WARM_NIGHT_C = 28.0
# US National Weather Service heat index bands, used as guidance only.
HEAT_INDEX_CAUTION_C = 32.0
HEAT_INDEX_DANGER_C = 41.0
NEARBY_REPORT_KM = 2.0
HIGH_UV = 8
WET_DAY_MM = 2.5
MIN_MODELS_TO_COMPARE = 2
SEASONS = {
    "air": {11, 12, 1, 2},
    "heat": {3, 4, 5},
    "monsoon": {6, 7, 8, 9},
    "festive": {10},
}


def heat_index_c(temperature_c: float | None, humidity: float | None) -> float | None:
    """NWS Rothfusz heat index. Below 27 °C the air temperature is returned unchanged."""
    if temperature_c is None or humidity is None:
        return None
    if temperature_c < 27:
        return round(temperature_c, 1)
    t = temperature_c * 9 / 5 + 32
    r = humidity
    index_f = (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * r
        - 0.22475541 * t * r
        - 0.00683783 * t * t
        - 0.05481717 * r * r
        + 0.00122874 * t * t * r
        + 0.00085282 * t * r * r
        - 0.00000199 * t * t * r * r
    )
    return round(max((index_f - 32) * 5 / 9, temperature_c), 1)


def heat_level(index: float | None) -> str:
    if index is None:
        return "unknown"
    if index >= HEAT_INDEX_DANGER_C:
        return "warning"
    if index >= HEAT_INDEX_CAUTION_C:
        return "caution"
    return "typical"


def rain_soon(hours: list, now) -> dict:
    """Forecast rain over the next two hours. Missing data stays null, never zero."""
    window = [
        record for record in hours if now <= record.valid_time <= now + timedelta(hours=RAIN_SOON_HOURS)
    ]
    upcoming = next(
        (
            record
            for record in hours
            if record.valid_time >= now
            and (
                (record.precipitation_probability or 0) >= RAIN_LIKELY_PROBABILITY
                or (record.precipitation_mm or 0) >= RAIN_LIKELY_MM
            )
        ),
        None,
    )
    if not window:
        return {"total_mm": None, "max_probability_pct": None, "next_rain_at": None}
    return {
        "total_mm": round(sum(record.precipitation_mm or 0 for record in window), 1),
        "max_probability_pct": max(record.precipitation_probability or 0 for record in window),
        "next_rain_at": upcoming.valid_time if upcoming else None,
    }


def _hour_index(record) -> float | None:
    return heat_index_c(record.temperature_c, record.relative_humidity)


def best_outdoor_window(hours: list) -> dict | None:
    """The coolest dry daytime stretch, of at most three hours, in the given records."""
    runs: list[list] = []
    current: list = []
    for record in hours:
        local_hour = record.valid_time.astimezone(IST).hour
        index = _hour_index(record)
        suitable = (
            OUTDOOR_FIRST_HOUR <= local_hour <= OUTDOOR_LAST_HOUR
            and index is not None
            and (record.precipitation_probability or 0) < OUTDOOR_MAX_RAIN_PROBABILITY
            and (record.precipitation_mm or 0) < RAIN_LIKELY_MM
        )
        if suitable:
            current.append(record)
            if len(current) == 3:
                runs.append(current)
                current = current[1:]
        else:
            if current:
                runs.append(current)
            current = []
    if current:
        runs.append(current)
    if not runs:
        return None
    best = min(runs, key=lambda run: (-len(run), mean(_hour_index(record) for record in run)))
    return {
        "start": best[0].valid_time,
        "end": best[-1].valid_time + timedelta(hours=1),
        "max_heat_index_c": max(_hour_index(record) for record in best),
    }


def model_agreement(area: Area, day) -> dict | None:
    """Compare three independent models. Disagreement is reported, never averaged away."""
    forecasts = DailyModelForecast.objects.filter(
        location__area=area, location__source__slug="open_meteo", valid_date=day, rain_mm__isnull=False
    )
    rain = [forecast.rain_mm for forecast in forecasts]
    if len(rain) < MIN_MODELS_TO_COMPARE:
        return None
    wet = sum(1 for value in rain if value >= WET_DAY_MM)
    if wet in {0, len(rain)}:
        level = "high"
    elif wet == 1 and max(rain) < HEAVY_RAIN_SOON_MM:
        level = "medium"
    else:
        level = "low"
    return {
        "level": level,
        "models_wet": wet,
        "models": len(rain),
        "rain_low_mm": round(min(rain), 1),
        "rain_high_mm": round(max(rain), 1),
    }


def cleanest_air_window(area: Area, now) -> dict | None:
    """The two daytime hours with the lowest forecast PM2.5 in the next 24 hours."""
    hours = [
        record
        for record in AirForecastHour.objects.filter(
            area=area, valid_time__gte=now, valid_time__lte=now + timedelta(hours=24), pm25__isnull=False
        ).order_by("valid_time")
        if OUTDOOR_FIRST_HOUR <= record.valid_time.astimezone(IST).hour <= OUTDOOR_LAST_HOUR
    ]
    pairs = [
        (first, second)
        for first, second in zip(hours, hours[1:], strict=False)
        if second.valid_time - first.valid_time == timedelta(hours=1)
    ]
    if not pairs:
        return None
    first, second = min(pairs, key=lambda pair: pair[0].pm25 + pair[1].pm25)
    return {
        "start": first.valid_time,
        "end": second.valid_time + timedelta(hours=1),
        "pm25": round(max(first.pm25, second.pm25), 1),
    }


def build_timeline(hours: list) -> list[dict]:
    """The next twelve forecast hours for an at-a-glance strip."""
    return [
        {
            "time": record.valid_time,
            "temperature_c": record.temperature_c,
            "heat_index_c": _hour_index(record),
            "rain_mm": record.precipitation_mm,
            "rain_probability_pct": record.precipitation_probability,
            "uv_index": record.uv_index,
            "condition": condition_for_code(record.weather_code),
        }
        for record in hours[:12]
    ]


def _night_low(hours: list) -> float | None:
    values = [
        record.temperature_c
        for record in hours
        if record.temperature_c is not None and record.valid_time.astimezone(IST).hour in NIGHT_HOURS
    ]
    return min(values) if values else None


def _tips(rain: dict, peak_index, night_low, uv_peak, air: dict, alerts: dict, reports: int, now) -> list[dict]:
    tips: list[dict] = []
    if alerts["count"]:
        tips.append(
            {
                "key": "official_alert",
                "level": "warning",
                "params": {"count": alerts["count"]},
                "text": f"{alerts['count']} official warning(s) cover this area. Read the original bulletin.",
            }
        )
    total = rain["total_mm"]
    if total is not None and total >= HEAVY_RAIN_SOON_MM:
        tips.append(
            {
                "key": "heavy_rain_soon",
                "level": "warning",
                "params": {"mm": total},
                "text": f"Heavy rain is forecast in the next 2 hours, about {total} mm. Allow extra time.",
            }
        )
    elif rain["next_rain_at"] and rain["next_rain_at"] <= now + timedelta(hours=12):
        tips.append(
            {
                "key": "carry_umbrella",
                "level": "info",
                "params": {"at": rain["next_rain_at"]},
                "text": "Rain is likely later. Carry an umbrella.",
            }
        )
    if reports:
        tips.append(
            {
                "key": "reports_nearby",
                "level": "caution",
                "params": {"count": reports},
                "text": f"{reports} active resident report(s) nearby. Check the live map before you leave.",
            }
        )
    level = heat_level(peak_index)
    if level in {"caution", "warning"}:
        tips.append(
            {
                "key": f"heat_{level}",
                "level": level,
                "params": {"index": peak_index},
                "text": f"Feels like up to {peak_index}°C today. Drink water and limit midday effort.",
            }
        )
    if night_low is not None and night_low >= WARM_NIGHT_C:
        tips.append(
            {
                "key": "warm_night",
                "level": "caution",
                "params": {"low": round(night_low, 1)},
                "text": f"A warm night, staying near {round(night_low, 1)}°C. Check on older relatives.",
            }
        )
    if air["level"] in {"caution", "warning"}:
        tips.append(
            {
                "key": "poor_air",
                "level": air["level"],
                "params": {"aqi": air["measurement"]["aqi"]},
                "text": (
                    f"Nearest station AQI is {air['measurement']['aqi']}. Sensitive groups may want to "
                    "reduce outdoor effort."
                ),
            }
        )
    if uv_peak is not None and uv_peak >= HIGH_UV:
        tips.append(
            {
                "key": "high_uv",
                "level": "caution",
                "params": {"uv": round(uv_peak)},
                "text": f"UV index reaches {round(uv_peak)}. Shade, a hat and sunscreen help around midday.",
            }
        )
    return tips


def build_today(area: Area, *, neighbourhood: Neighbourhood | None = None, now=None) -> dict:
    now = now or timezone.now()
    centre = _center(area, neighbourhood)
    hours = [record for record in hourly_records(area.slug, hours=24) if record.valid_time >= now]
    retrieved_at = latest_retrieved_at(hours)
    state = freshness_state(retrieved_at, max_age=FORECAST_MAX_AGE) if hours else DataState.UNAVAILABLE

    rain = rain_soon(hours, now)
    indices = [index for index in (_hour_index(record) for record in hours) if index is not None]
    peak_index = max(indices) if indices else None
    night_low = _night_low(hours)
    uv_values = [record.uv_index for record in hours if record.uv_index is not None]
    uv_peak = max(uv_values) if uv_values else None
    air = _air_quality_section(centre, now)
    alerts = _alerts_section(area, neighbourhood, now)

    live = list(live_reports(area))
    nearby = [
        report
        for report in live
        if haversine_m(centre[0], centre[1], report.latitude, report.longitude) <= NEARBY_REPORT_KM * 1000
    ]
    label = neighbourhood.name if neighbourhood else area.name.removesuffix(" Municipal Corporation")

    return {
        "generated_at": now,
        "place": {
            "label": label,
            "area": area.slug,
            "neighbourhood": neighbourhood.slug if neighbourhood else None,
        },
        "state": state,
        "retrieved_at": retrieved_at,
        "season": next((name for name, months in SEASONS.items() if now.astimezone(IST).month in months), "air"),
        "rain": rain,
        "heat": {
            "peak_heat_index_c": peak_index,
            "level": heat_level(peak_index),
            "night_low_c": night_low,
            "uv_peak": uv_peak,
            "note": "Calculated from forecast temperature and humidity. Guidance, not a measurement.",
        },
        "best_outdoor_window": best_outdoor_window(hours),
        "cleanest_air_window": cleanest_air_window(area, now),
        "tomorrow_agreement": model_agreement(area, now.astimezone(IST).date() + timedelta(days=1)),
        "timeline": build_timeline(hours),
        "air": {"state": air["state"], "level": air["level"], "aqi": (air["measurement"] or {}).get("aqi")},
        "alerts": {"state": alerts["state"], "count": alerts["count"], "feed_message": alerts["feed_message"]},
        "reports": {"nearby": len(nearby), "city": len(live), "radius_km": NEARBY_REPORT_KM},
        "tips": _tips(rain, peak_index, night_low, uv_peak, air, alerts, len(nearby), now),
        "note": "Forecast-based guidance for planning. It is not a guarantee that any place is safe.",
    }


def build_week_plan(area: Area, *, now=None) -> dict:
    """Day-by-day planning view for outings, commutes and festival visits."""
    now = now or timezone.now()
    hours = [record for record in hourly_records(area.slug, hours=24 * 7) if record.valid_time >= now]
    by_day: dict = defaultdict(list)
    for record in hours:
        by_day[record.valid_time.astimezone(IST).date()].append(record)

    days = []
    for day, records in sorted(by_day.items()):
        indices = [index for index in (_hour_index(record) for record in records) if index is not None]
        rain_total = round(sum(record.precipitation_mm or 0 for record in records), 1)
        max_probability = max((record.precipitation_probability or 0) for record in records)
        peak_index = max(indices) if indices else None
        window = best_outdoor_window(records)
        if rain_total >= 20 or heat_level(peak_index) == "warning":
            rating = "poor"
        elif rain_total >= 5 or heat_level(peak_index) == "caution":
            rating = "fair"
        else:
            rating = "good"
        midday = min(records, key=lambda record: abs(record.valid_time.astimezone(IST).hour - 13))
        days.append(
            {
                "date": day,
                "rating": rating,
                "rain_mm": rain_total,
                "max_rain_probability_pct": max_probability,
                "peak_heat_index_c": peak_index,
                "condition": condition_for_code(midday.weather_code),
                "best_window": window,
                "agreement": model_agreement(area, day),
                "hours_covered": len(records),
            }
        )

    retrieved_at = latest_retrieved_at(hours)
    return {
        "area": {"slug": area.slug, "name": area.name},
        "generated_at": now,
        "state": freshness_state(retrieved_at, max_age=FORECAST_MAX_AGE) if hours else DataState.UNAVAILABLE,
        "retrieved_at": retrieved_at,
        "days": days,
        "note": "Ratings are simple rules over a city-wide forecast, which gets less reliable further ahead.",
    }
