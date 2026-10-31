"""Heat in everyday terms: today's risky hours, and which places run hotter or cooler."""

from __future__ import annotations

from collections import defaultdict
from statistics import median
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.utils import timezone

from apps.environment.models import EnvironmentalObservation
from apps.intelligence.today import heat_index_c
from apps.locations.models import Area, GridCell
from apps.weather.selectors import hourly_records

IST = ZoneInfo("Asia/Kolkata")
CACHE_SECONDS = 6 * 60 * 60
SUMMER_MONTHS = {3, 4, 5, 6}
MIN_COVERAGE = 0.5
LIST_LENGTH = 6
# US National Weather Service heat index bands, in degrees Celsius.
BANDS = [(41, "dangerous"), (32, "high"), (27, "caution")]
AVOID_FROM_C = 32


def _level(value: float) -> str:
    return next((name for floor, name in BANDS if value >= floor), "comfortable")


def today_heat(area: Area, *, now=None) -> dict | None:
    now = now or timezone.now()
    local_day = now.astimezone(IST).date()
    hours = [
        record
        for record in hourly_records(area.data_area.slug, hours=24)
        if record.valid_time >= now and record.valid_time.astimezone(IST).date() == local_day
    ]
    readings = [
        (record, value)
        for record in hours
        if (value := heat_index_c(record.temperature_c, record.relative_humidity)) is not None
    ]
    if not readings:
        return None
    peak_record, peak = max(readings, key=lambda item: item[1])
    risky = [record for record, value in readings if value >= AVOID_FROM_C]
    uv = [record.uv_index for record in hours if record.uv_index is not None]
    return {
        "peak_feels_c": peak,
        "peak_at": peak_record.valid_time,
        "level": _level(peak),
        "avoid_from": risky[0].valid_time if risky else None,
        "avoid_to": risky[-1].valid_time if risky else None,
        "uv_peak": max(uv) if uv else None,
    }


def _ground_summary(area: Area) -> dict:
    """Typical summer ground heat per place, and the city's pattern through the year."""
    key = f"ground-summary:{area.pk}"
    stored = cache.get(key)
    if stored is not None:
        return stored
    cells = {cell.id: cell for cell in GridCell.objects.filter(area=area, coverage_fraction__gte=MIN_COVERAGE)}
    summer, months = defaultdict(list), defaultdict(list)
    rows = EnvironmentalObservation.objects.filter(cell__area=area, lst_c__isnull=False)
    for cell_id, observed, lst in rows.values_list("cell_id", "observed_on", "lst_c").iterator():
        months[observed.month].append(lst)
        if observed.month in SUMMER_MONTHS and cell_id in cells:
            summer[cell_id].append(lst)

    places = list(area.neighbourhoods.filter(is_active=True))
    named: dict[str, dict] = {}
    for cell_id, values in summer.items():
        cell = cells[cell_id]
        nearest = min(
            places,
            key=lambda place: (place.latitude - cell.centroid_lat) ** 2 + (place.longitude - cell.centroid_lon) ** 2,
            default=None,
        )
        if nearest is None:
            continue
        ground = round(median(values), 1)
        entry = {"name": nearest.name, "slug": nearest.slug, "ground_c": ground}
        if nearest.slug not in named or ground > named[nearest.slug]["ground_c"]:
            named[nearest.slug] = {**entry, "latitude": nearest.latitude, "longitude": nearest.longitude}
    ranked = sorted(named.values(), key=lambda item: item["ground_c"], reverse=True)
    summary = {
        "ranked": ranked,
        "months": [{"month": month, "ground_c": round(median(values), 1)} for month, values in sorted(months.items())],
    }
    cache.set(key, summary, CACHE_SECONDS)
    return summary


def heat_guide(area: Area, *, now=None) -> dict:
    data_area = area.data_area
    summary = _ground_summary(data_area)
    ranked = summary["ranked"]
    if area != data_area:
        ranked = [place for place in ranked if area.covers(place["latitude"], place["longitude"])]
    return {
        "today": today_heat(area, now=now),
        "hottest": ranked[:LIST_LENGTH],
        "coolest": list(reversed(ranked[-LIST_LENGTH:])) if len(ranked) > LIST_LENGTH else [],
        "months": summary["months"],
    }
