"""Area-first place status.

This service composes existing module data for one neighbourhood (or the whole
area) without creating any new environmental value. Every number is copied from
a stored record and keeps its source, unit and timestamp. The only derived value
is the waterlogging *risk indicator*, a transparent point score over forecast
rain, recent daily rain and nearby resident reports. It is not a trained model,
not a probability, and not a flood forecast.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.db.models import Q
from django.utils import timezone

from apps.air_quality.models import AQIStation
from apps.alerts.models import AlertStatus, OfficialAlert
from apps.alerts.services import AlertMatch, alert_match
from apps.core.geometry import bbox_around_point, haversine_m
from apps.core.models import DataSource
from apps.core.quality import DataState, freshness_state, source_availability
from apps.core.serializers import source_summary
from apps.environment.models import EnvironmentalObservation
from apps.environment.terrain import nearest_terrain
from apps.incidents.models import IncidentCategory, IncidentReport, IncidentStatus
from apps.incidents.serializers import IncidentListSerializer
from apps.incidents.services import visible_incidents
from apps.intelligence.scorecard import place_scorecard
from apps.locations.models import Area, Neighbourhood
from apps.weather.models import WeatherRecord
from apps.weather.selectors import (
    current_record,
    daily_records,
    history_records,
    hourly_records,
    latest_retrieved_at,
)
from apps.weather.serializers import WeatherRecordSerializer

PLACE_METHOD_VERSION = "place-status-v1"

WATERLOGGING_METHOD = "rule_based_rain_and_reports_v1"
WATERLOGGING_WINDOW_HOURS = 24
REPORT_WINDOW_HOURS = 72
RADIUS_KM = {"area": 5.0, "neighbourhood": 2.5}

WEATHER_MAX_AGE = timedelta(minutes=180)
AIR_MAX_AGE = timedelta(hours=6)
LST_MAX_AGE_DAYS = 40

WATER_CATEGORIES = {
    IncidentCategory.WATERLOGGING,
    IncidentCategory.FLOODING,
    IncidentCategory.BLOCKED_DRAINAGE,
}
HIDDEN_STATUSES = {
    IncidentStatus.REJECTED,
    IncidentStatus.DUPLICATE,
    IncidentStatus.EXPIRED,
}

HEAT_THRESHOLDS = {"info": 35.0, "caution": 38.0, "warning": 40.0}
RAIN_THRESHOLDS = {"info": 5.0, "caution": 20.0, "warning": 50.0}
AIR_THRESHOLDS = {"info": 100, "caution": 200, "warning": 300}
NEARBY_STATION_KM = 75.0


def _source_for(slug: str) -> DataSource | None:
    return DataSource.objects.filter(slug=slug, is_active=True).first()


def _availability(slug: str) -> dict:
    source = _source_for(slug)
    if source is None:
        return {"state": DataState.UNAVAILABLE, "last_success_at": None, "source": None}
    return {**source_availability(source), "source": source}


def _freshness(record: WeatherRecord | None, max_age: timedelta) -> str:
    if record is None:
        return DataState.UNAVAILABLE
    return freshness_state(record.retrieved_at, max_age=max_age)


def _combined_state(states: list[str]) -> str:
    if not states:
        return DataState.UNAVAILABLE
    if any(state == DataState.STALE for state in states):
        return DataState.STALE
    if all(state == DataState.AVAILABLE for state in states):
        return DataState.AVAILABLE
    if any(state in {DataState.AVAILABLE, DataState.STALE} for state in states):
        return DataState.PARTIAL
    return DataState.UNAVAILABLE


def _rain_points(mm: float | None) -> int:
    if mm is None:
        return 0
    if mm >= RAIN_THRESHOLDS["warning"]:
        return 3
    if mm >= RAIN_THRESHOLDS["caution"]:
        return 2
    if mm >= RAIN_THRESHOLDS["info"]:
        return 1
    return 0


def _recent_rain_points(mm: float | None) -> int:
    if mm is None:
        return 0
    if mm >= RAIN_THRESHOLDS["warning"]:
        return 2
    if mm >= RAIN_THRESHOLDS["caution"]:
        return 1
    return 0


def _risk_level(points: int) -> str:
    if points >= 4:
        return "high"
    if points >= 2:
        return "elevated"
    return "low"


RISK_LABELS = {
    "low": "Low waterlogging signal",
    "elevated": "Elevated waterlogging signal",
    "high": "High waterlogging signal",
    "reports_only": "Reports nearby, rainfall data unavailable",
    "unknown": "Waterlogging signal unavailable",
}


def _heat_level(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value >= HEAT_THRESHOLDS["warning"]:
        return "warning"
    if value >= HEAT_THRESHOLDS["caution"]:
        return "caution"
    if value >= HEAT_THRESHOLDS["info"]:
        return "info"
    return "typical"


def _air_level(aqi: int | None) -> str:
    if aqi is None:
        return "unknown"
    if aqi >= AIR_THRESHOLDS["warning"]:
        return "warning"
    if aqi >= AIR_THRESHOLDS["caution"]:
        return "caution"
    if aqi >= AIR_THRESHOLDS["info"]:
        return "info"
    return "typical"


def _center(area: Area, neighbourhood: Neighbourhood | None) -> tuple[float, float]:
    if neighbourhood is not None:
        return neighbourhood.latitude, neighbourhood.longitude
    return area.focus


def _distance_km(center: tuple[float, float], latitude: float, longitude: float) -> float:
    return haversine_m(center[0], center[1], latitude, longitude) / 1000


def _nearby_reports(
    area: Area,
    center: tuple[float, float],
    *,
    radius_km: float,
    window_hours: int,
    now,
    user=None,
) -> list[IncidentReport]:
    min_lat, min_lon, max_lat, max_lon = bbox_around_point(
        center[0], center[1], radius_km * 1000
    )
    queryset = IncidentReport.objects.filter(
        area=area.data_area,
        occurred_at__gte=now - timedelta(hours=window_hours),
        cleared_at__isnull=True,
        latitude__gte=min_lat,
        latitude__lte=max_lat,
        longitude__gte=min_lon,
        longitude__lte=max_lon,
    ).exclude(status__in=HIDDEN_STATUSES)
    queryset = (
        visible_incidents(queryset, user)
        .select_related("area", "neighbourhood", "source")
        .prefetch_related("attachments", "confirmations")
    )
    reports = []
    for report in queryset.order_by("-occurred_at"):
        if _distance_km(center, report.latitude, report.longitude) <= radius_km:
            reports.append(report)
    return reports


def _weather_section(area: Area, now) -> dict:
    current = current_record(area.slug)
    current_state = _freshness(current, WEATHER_MAX_AGE)
    source = current.source if current else _source_for("open_meteo")
    return {
        "state": current_state,
        "record": WeatherRecordSerializer(current).data if current else None,
        "source": source_summary(source, dataset="Open-Meteo forecast") if source else {},
        "retrieved_at": current.retrieved_at if current else None,
        "note": (
            "Provider model output for the Kolkata forecast point. It is not an official "
            "station observation or a warning."
        ),
        "reason": (
            None
            if current
            else "No current weather record has been ingested for this area."
        ),
    }


def _rain_section(area: Area, now) -> dict:
    hourly = list(hourly_records(area.slug, hours=24))
    future = [record for record in hourly if record.valid_time >= now]
    source = hourly[0].source if hourly else _source_for("open_meteo")
    retrieved_at = latest_retrieved_at(hourly)
    if not future:
        return {
            "state": DataState.UNAVAILABLE,
            "next_24h_total_mm": None,
            "next_24h_max_probability_pct": None,
            "peak_hour": None,
            "peak_hour_mm": None,
            "source": source_summary(source, dataset="Open-Meteo forecast") if source else {},
            "retrieved_at": retrieved_at,
            "note": "No hourly rainfall forecast is stored for the next 24 hours.",
            "reason": "No hourly rainfall forecast has been ingested for this area.",
        }
    total = round(sum((record.precipitation_mm or 0.0) for record in future), 2)
    peak = max(future, key=lambda record: record.precipitation_mm or 0.0)
    max_probability = max(
        (record.precipitation_probability or 0.0) for record in future
    )
    state = freshness_state(retrieved_at, max_age=WEATHER_MAX_AGE)
    return {
        "state": state,
        "next_24h_total_mm": total,
        "next_24h_max_probability_pct": max_probability,
        "peak_hour": peak.valid_time,
        "peak_hour_mm": peak.precipitation_mm,
        "source": source_summary(source, dataset="Open-Meteo forecast") if source else {},
        "retrieved_at": retrieved_at,
        "note": (
            "Forecast rainfall is model output, not a rain-gauge observation and not a "
            "flood or waterlogging prediction."
        ),
        "reason": None,
    }


def _recent_rain_section(area: Area, now) -> dict:
    """Yesterday's archive day plus today's forecast day.

    ``daily_records`` starts at the current local day, so a 48-hour window needs
    one archive day as well. Nothing is interpolated: if a day is missing it is
    simply absent from the total.
    """
    today = now.astimezone(ZoneInfo("Asia/Kolkata")).date()
    archived = list(history_records(area.slug, start=today - timedelta(days=1), end=today - timedelta(days=1)))
    current_day = list(daily_records(area.slug, days=0))
    recent = [record for record in archived + current_day if record.precipitation_mm is not None]
    if not recent:
        return {
            "state": DataState.UNAVAILABLE,
            "max_daily_mm": None,
            "total_mm": None,
            "window_hours": 48,
            "days_covered": 0,
            "source": {},
            "observed_at": None,
            "note": (
                "No recent daily rainfall records are stored. This is not evidence that it "
                "did not rain."
            ),
        }
    max_daily = max((record.precipitation_mm or 0.0) for record in recent)
    total = round(sum((record.precipitation_mm or 0.0) for record in recent), 2)
    source = recent[-1].source
    latest = max(recent, key=lambda record: record.valid_time)
    return {
        "state": freshness_state(latest.retrieved_at, max_age=timedelta(hours=24)),
        "max_daily_mm": round(max_daily, 2),
        "total_mm": total,
        "window_hours": 48,
        "days_covered": len(recent),
        "source": source_summary(
            source, dataset="Open-Meteo daily forecast/archive (ERA5-Land archive)"
        ),
        "observed_at": latest.valid_time,
        "note": (
            "Daily rainfall from stored model/archive records, not a local rain gauge. Today's "
            "value is a forecast and yesterday's value comes from the archive day."
        ),
    }


def _waterlogging_section(
    area: Area,
    center: tuple[float, float],
    resolution: str,
    reports: list[IncidentReport],
    rain: dict,
    recent_rain: dict,
    now,
) -> dict:
    water_reports = [
        report
        for report in reports
        if report.category in WATER_CATEGORIES
        and report.occurred_at >= now - timedelta(hours=WATERLOGGING_WINDOW_HOURS)
    ]
    verified = [
        report
        for report in water_reports
        if report.status in {IncidentStatus.VERIFIED, IncidentStatus.RESOLVED}
    ]
    unverified = [
        report
        for report in water_reports
        if report.status in {IncidentStatus.SUBMITTED, IncidentStatus.UNDER_REVIEW}
    ]

    forecast_mm = rain.get("next_24h_total_mm")
    recent_mm = recent_rain.get("max_daily_mm")
    points = 0
    inputs: list[dict[str, Any]] = []

    if forecast_mm is not None:
        contribution = _rain_points(forecast_mm)
        points += contribution
        inputs.append(
            {
                "key": "forecast_rain_24h",
                "label": "Forecast rain, next 24 h",
                "value": forecast_mm,
                "unit": "mm",
                "state": rain["state"],
                "source": rain["source"],
                "observed_at": rain.get("retrieved_at"),
                "contribution": contribution,
                "detail": "Open-Meteo hourly forecast summed over the next 24 hours.",
            }
        )

    if recent_mm is not None:
        contribution = _recent_rain_points(recent_mm)
        points += contribution
        inputs.append(
            {
                "key": "recent_daily_rain",
                "label": "Highest daily rain, last 48 h",
                "value": recent_mm,
                "unit": "mm",
                "state": recent_rain["state"],
                "source": recent_rain["source"],
                "observed_at": recent_rain.get("observed_at"),
                "contribution": contribution,
                "detail": "Stored daily model/archive value, not a rain-gauge observation.",
            }
        )

    terrain = nearest_terrain(area, *center) if resolution == "neighbourhood" else None
    if terrain is not None:
        contribution = 1 if terrain.terrain_class == "high" else 0
        points += contribution
        inputs.append(
            {
                "key": "terrain",
                "label": "Low-lying ground",
                "value": terrain.relative_elevation_m,
                "unit": "m against nearby land",
                "state": DataState.AVAILABLE,
                "source": {"name": terrain.dem_source},
                "observed_at": None,
                "contribution": contribution,
                "detail": "Satellite elevation for the nearest 1 km cell. It knows nothing about drains.",
            }
        )

    verified_points = min(len(verified), 2)
    points += verified_points
    inputs.append(
        {
            "key": "verified_water_reports",
            "label": "Verified water reports nearby",
            "value": len(verified),
            "unit": "reports",
            "state": DataState.AVAILABLE,
            "source": source_summary(_source_for("community_reports")),
            "observed_at": verified[0].occurred_at if verified else None,
            "contribution": verified_points,
            "detail": (
                f"Moderator-verified waterlogging/flooding/drainage reports within "
                f"{RADIUS_KM[resolution]} km in the last {WATERLOGGING_WINDOW_HOURS} hours."
            ),
        }
    )

    unverified_points = 1 if unverified else 0
    points += unverified_points
    inputs.append(
        {
            "key": "unverified_water_reports",
            "label": "Unverified water reports nearby",
            "value": len(unverified),
            "unit": "reports",
            "state": DataState.PARTIAL,
            "source": source_summary(_source_for("community_reports")),
            "observed_at": unverified[0].occurred_at if unverified else None,
            "contribution": unverified_points,
            "detail": (
                "Resident reports that a moderator has not checked. They add at most one "
                "point and never become an official warning."
            ),
        }
    )

    weather_available = forecast_mm is not None or recent_mm is not None
    weather_state = _combined_state(
        [state for state in (rain["state"], recent_rain["state"]) if state != DataState.UNAVAILABLE]
    )
    if not weather_available:
        state = DataState.PARTIAL if water_reports else DataState.UNAVAILABLE
        level = "reports_only" if water_reports else "unknown"
    else:
        state = weather_state
        level = _risk_level(points)

    drivers = [
        item["label"] + f": {item['value']} {item['unit']}"
        for item in inputs
        if item["contribution"] > 0
    ]
    if points == 0:
        drivers = ["No rainfall or nearby report contribution crossed a scoring threshold."]

    caveats = [
        "This is a rule-based risk indicator built from rainfall and nearby reports. It is not a trained ML model, not a probability, and not a flood forecast.",
        "It does not know local drain capacity, tide, or drainage works, so a low signal does not mean a street is dry.",
        "Community reports describe individual locations and may be incomplete or mistaken.",
        "Official warnings are a separate layer; absence of a warning does not mean conditions are safe.",
    ]
    if not weather_available:
        caveats.insert(
            0,
            "Rainfall inputs were unavailable, so only community evidence contributed to this signal.",
        )

    return {
        "state": state,
        "level": level,
        "label": RISK_LABELS[level],
        "points": points,
        "max_points": 9,
        "method": {
            "id": WATERLOGGING_METHOD,
            "version": PLACE_METHOD_VERSION,
            "label": "Rule-based waterlogging risk indicator",
            "is_ml": False,
            "description": (
                "Adds transparent points for forecast rain, recent daily rain and nearby "
                "water reports. For neighbourhoods it also adds a point for low-lying ground. No trained waterlogging model exists yet; no accuracy is claimed."
            ),
        },
        "inputs": inputs,
        "drivers": drivers,
        "reports": {
            "window_hours": WATERLOGGING_WINDOW_HOURS,
            "radius_km": RADIUS_KM[resolution],
            "verified": len(verified),
            "unverified": len(unverified),
            "total": len(water_reports),
        },
        "caveats": caveats,
    }


def _heat_section(area: Area, center: tuple[float, float], now) -> dict:
    current = current_record(area.slug)
    air_state = _freshness(current, WEATHER_MAX_AGE)
    air_value = None
    value_label = None
    if current is not None:
        if current.apparent_temperature_c is not None:
            air_value = current.apparent_temperature_c
            value_label = "apparent temperature"
        elif current.temperature_c is not None:
            air_value = current.temperature_c
            value_label = "air temperature"
    source = current.source if current else _source_for("open_meteo")
    air = {
        "state": air_state,
        "temperature_c": current.temperature_c if current else None,
        "apparent_temperature_c": current.apparent_temperature_c if current else None,
        "value_c": air_value,
        "value_label": value_label,
        "level": _heat_level(air_value),
        "observed_at": current.valid_time if current else None,
        "retrieved_at": current.retrieved_at if current else None,
        "source": source_summary(source, dataset="Open-Meteo forecast") if source else {},
        "note": (
            "Model output, not a station measurement. Heat stress also depends on humidity, "
            "ventilation and personal health."
        ),
        "reason": None
        if current
        else "No current weather record is available for the heat-stress check.",
    }

    observations = EnvironmentalObservation.objects.filter(
        cell__area=area.data_area, lst_c__isnull=False
    ).select_related("cell", "scene")
    latest_date = observations.order_by("-observed_on").values_list(
        "observed_on", flat=True
    ).first()
    land_surface = {
        "state": DataState.UNAVAILABLE,
        "latest_date": latest_date,
        "nearest_cell_lst_c": None,
        "nearest_cell_code": None,
        "distance_km": None,
        "city_p90_c": None,
        "observed_count": 0,
        "source": source_summary(_source_for("landsat"), dataset="USGS Landsat C2"),
        "note": (
            "Land-surface temperature (LST), not air temperature. A single scene date is a "
            "snapshot, not live conditions."
        ),
        "reason": (
            "No Landsat land-surface observations have been ingested. Earth Engine "
            "credentials and a real export are still required."
        ),
    }
    if latest_date is not None:
        latest = list(observations.filter(observed_on=latest_date))
        if latest:
            values = sorted(observation.lst_c for observation in latest)
            index = min(len(values) - 1, max(0, int(round(0.9 * (len(values) - 1)))))
            nearest = min(
                latest,
                key=lambda observation: _distance_km(
                    center,
                    observation.cell.centroid_lat,
                    observation.cell.centroid_lon,
                ),
            )
            distance = _distance_km(
                center, nearest.cell.centroid_lat, nearest.cell.centroid_lon
            )
            age_days = (now.date() - latest_date).days
            land_surface.update(
                {
                    "state": DataState.AVAILABLE
                    if age_days <= LST_MAX_AGE_DAYS
                    else DataState.STALE,
                    "nearest_cell_lst_c": nearest.lst_c,
                    "nearest_cell_code": nearest.cell.code,
                    "distance_km": round(distance, 2),
                    "city_p90_c": round(values[index], 2),
                    "observed_count": len(latest),
                    "reason": None,
                }
            )
            if age_days > LST_MAX_AGE_DAYS:
                land_surface["note"] = (
                    f"Latest Landsat scene is {age_days} days old, so this snapshot may not "
                    "reflect current surface heat."
                )

    return {
        "state": _combined_state([air_state, land_surface["state"]]),
        "air": air,
        "land_surface": land_surface,
    }


def _air_quality_section(center: tuple[float, float], now) -> dict:
    availability = _availability("cpcb")
    stations = list(AQIStation.objects.filter(is_active=True).select_related("source"))
    nearest = None
    nearest_distance = None
    for station in stations:
        distance = _distance_km(center, station.latitude, station.longitude)
        if distance > NEARBY_STATION_KM:
            continue
        if nearest_distance is None or distance < nearest_distance:
            nearest, nearest_distance = station, distance

    base = {
        "state": DataState.UNAVAILABLE,
        "station": None,
        "measurement": None,
        "distance_km": None,
        "level": "unknown",
        "source": {},
        "note": (
            "Station values are point measurements, not an interpolated neighbourhood AQI "
            "surface."
        ),
        "reason": None,
    }
    if nearest is None:
        base["reason"] = "No CPCB monitoring stations have been ingested for this area. Run fetch_cpcb."
        return base

    measurement = (
        nearest.measurements.filter(measured_at__gte=now - timedelta(hours=24))
        .select_related("source")
        .order_by("-measured_at")
        .first()
    )
    if measurement is None:
        base.update(
            {
                "station": {
                    "name": nearest.name,
                    "latitude": nearest.latitude,
                    "longitude": nearest.longitude,
                },
                "distance_km": round(nearest_distance, 2),
                "source": source_summary(nearest.source, dataset="CPCB station data"),
                "reason": "The nearest station has no measurement in the last 24 hours.",
            }
        )
        return base

    state = freshness_state(measurement.measured_at, max_age=AIR_MAX_AGE)
    if state == DataState.AVAILABLE and availability["state"] == DataState.UNAVAILABLE:
        state = DataState.STALE
    base.update(
        {
            "state": state,
            "station": {
                "name": nearest.name,
                "latitude": nearest.latitude,
                "longitude": nearest.longitude,
            },
            "measurement": {
                "measured_at": measurement.measured_at,
                "retrieved_at": measurement.retrieved_at,
                "aqi": measurement.aqi,
                "aqi_category": measurement.aqi_category,
                "pm25": measurement.pm25,
                "pm10": measurement.pm10,
                "nh3": measurement.nh3,
                "aqi_basis": (measurement.raw or {}).get("aqi_basis") or {},
                "units": (measurement.raw or {}).get("units") or {},
                "quality_status": measurement.quality_status,
            },
            "distance_km": round(nearest_distance, 2),
            "level": _air_level(measurement.aqi),
            "source": source_summary(measurement.source, dataset="CPCB station data"),
            "reason": None,
        }
    )
    return base


def _alert_scope(alert: OfficialAlert, area: Area, neighbourhood: Neighbourhood | None) -> str | None:
    if neighbourhood and neighbourhood.name.lower() in (alert.areas_text or "").lower():
        return AlertMatch.NAMED
    return alert_match(alert, area)


def _alerts_section(
    area: Area, neighbourhood: Neighbourhood | None, now
) -> dict:
    availability = _availability("sachet")
    alerts = list(
        OfficialAlert.objects.filter(status=AlertStatus.ACTIVE)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .select_related("source")
        .order_by("-issued_at")
    )
    scoped = []
    for alert in alerts:
        alert.match = _alert_scope(alert, area, neighbourhood)
        if alert.match:
            scoped.append(alert)
    scoped.sort(key=lambda alert: alert.match != AlertMatch.NAMED)
    named = sum(1 for alert in scoped if alert.match == AlertMatch.NAMED)
    feed_healthy = availability["state"] in {DataState.AVAILABLE, DataState.PARTIAL}
    if feed_healthy:
        state = availability["state"]
        reason = None
        if named:
            feed_message = f"{named} active official warning(s) name this area."
        elif scoped:
            feed_message = f"{len(scoped)} state-level warning(s) may include this area."
        else:
            feed_message = "The official alert feed is reachable. No active warning covers this area right now."
    elif scoped:
        state = DataState.STALE
        reason = (
            "The latest official alert-feed refresh failed, so these warnings may be stale. "
            "Check the issuing agency before acting."
        )
        feed_message = reason
    else:
        state = availability["state"]
        reason = "The official alert feed is unavailable and no stored warning covers this area."
        feed_message = reason
    return {
        "state": state,
        "count": len(scoped),
        "named_count": named,
        "results": [
            {
                "id": str(alert.id),
                "match": alert.match,
                "title": alert.title,
                "hazard": alert.hazard,
                "hazard_label": alert.get_hazard_display(),
                "severity": alert.severity,
                "severity_label": alert.get_severity_display(),
                "issued_at": alert.issued_at,
                "expires_at": alert.expires_at,
                "areas_text": alert.areas_text,
                "source_url": alert.source_url,
                "source": source_summary(alert.source),
                "quality_status": alert.quality_status,
            }
            for alert in scoped[:8]
        ],
        "source": source_summary(availability.get("source"))
        if availability.get("source")
        else {},
        "last_success_at": availability.get("last_success_at"),
        "feed_message": feed_message,
        "note": (
            "Only source-issued warnings are shown. Absence of a warning is not proof that "
            "conditions are safe, and warnings can cover a whole district."
        ),
        "reason": reason,
    }


def _reports_section(
    area: Area,
    centre: tuple[float, float],
    resolution: str,
    reports: list[IncidentReport],
    user=None,
) -> dict:
    verified = [
        report
        for report in reports
        if report.status in {IncidentStatus.VERIFIED, IncidentStatus.RESOLVED}
    ]
    unverified = [
        report
        for report in reports
        if report.status in {IncidentStatus.SUBMITTED, IncidentStatus.UNDER_REVIEW}
    ]
    return {
        "state": DataState.AVAILABLE if reports else DataState.UNAVAILABLE,
        "window_hours": REPORT_WINDOW_HOURS,
        "radius_km": RADIUS_KM[resolution],
        "total": len(reports),
        "verified": len(verified),
        "unverified": len(unverified),
        "results": IncidentListSerializer(
            reports[:12], many=True, context={"user": user}
        ).data,
        "note": (
            f"Public resident reports within {RADIUS_KM[resolution]} km of the place centre in "
            f"the last {REPORT_WINDOW_HOURS} hours. They are observations, not official alerts."
        ),
        "reason": (
            None
            if reports
            else "No public community reports were submitted within this radius and window. "
            "Absence of reports is not evidence that conditions are fine."
        ),
    }


def _status_summary(
    waterlogging: dict,
    heat: dict,
    rain: dict,
    air: dict,
    alerts: dict,
    reports: dict,
    weather: dict,
) -> dict:
    reasons: list[str] = []
    level = "typical"

    if alerts["named_count"]:
        level = "attention"
        reasons.append(f"{alerts['named_count']} active official warning(s) name this area.")
    elif alerts["count"]:
        level = "watch"
        reasons.append(f"{alerts['count']} state-level warning(s) may include this area.")
    if waterlogging["level"] == "high":
        level = "attention"
        reasons.append("The waterlogging risk indicator is high.")
    elif waterlogging["level"] == "elevated" and level == "typical":
        level = "watch"
        reasons.append("The waterlogging risk indicator is elevated.")
    elif waterlogging["level"] == "reports_only" and waterlogging["reports"]["verified"]:
        if level == "typical":
            level = "watch"
        reasons.append(
            "Verified nearby water reports exist, but rainfall inputs were unavailable."
        )

    air_heat_level = heat["air"]["level"]
    if air_heat_level == "warning":
        level = "attention"
        reasons.append("Current heat stress is at the warning band.")
    elif air_heat_level == "caution" and level == "typical":
        level = "watch"
        reasons.append("Current heat stress is at the caution band.")

    rain_mm = rain.get("next_24h_total_mm")
    if rain_mm is not None:
        if rain_mm >= RAIN_THRESHOLDS["warning"]:
            level = "attention"
            reasons.append(f"The forecast expects about {rain_mm:.1f} mm of rain in 24 hours.")
        elif rain_mm >= RAIN_THRESHOLDS["caution"] and level == "typical":
            level = "watch"
            reasons.append(f"The forecast expects about {rain_mm:.1f} mm of rain in 24 hours.")

    air_level = air["level"]
    if air_level == "warning":
        level = "attention"
        reasons.append("The nearest CPCB station reports a high AQI.")
    elif air_level == "caution" and level == "typical":
        level = "watch"
        reasons.append("The nearest CPCB station reports an elevated AQI.")

    if reports["verified"] and level == "typical":
        level = "watch"
        reasons.append(f"{reports['verified']} verified community report(s) are nearby.")

    # Only an otherwise quiet status becomes unknown: a warning must never be replaced.
    if (
        level == "typical"
        and weather["state"] == DataState.UNAVAILABLE
        and reports["state"] == DataState.UNAVAILABLE
    ):
        level = "unknown"
        reasons = ["No live local inputs are currently available for this place."]

    if not reasons:
        reasons = [
            "No stored rainfall, heat, air-quality or report signal crossed its threshold. "
            "This is not a guarantee that conditions are safe."
        ]

    headline = {
        "attention": "Conditions need attention",
        "watch": "Worth checking before you travel",
        "typical": "No strong local signal right now",
        "unknown": "Local conditions are unavailable",
    }[level]
    if alerts["named_count"]:
        headline = "Official warning in effect"
    elif waterlogging["level"] == "high":
        headline = "Waterlogging risk is high"
    elif rain_mm is not None and rain_mm >= RAIN_THRESHOLDS["warning"]:
        headline = "Heavy rain is forecast"
    elif air_heat_level == "warning":
        headline = "Heat stress is high"
    elif air_level == "warning":
        headline = "Air quality is poor at the nearest station"

    return {
        "level": level,
        "headline": headline,
        "reasons": reasons[:4],
        "state": _combined_state(
            [weather["state"], waterlogging["state"], alerts["state"], air["state"], heat["state"]]
        ),
    }


def build_place_status(
    area: Area,
    *,
    neighbourhood: Neighbourhood | None = None,
    user=None,
    now=None,
) -> dict:
    now = now or timezone.now()
    resolution = "neighbourhood" if neighbourhood is not None else "area"
    centre = _center(area, neighbourhood)
    radius_km = RADIUS_KM[resolution]
    label = f"{neighbourhood.name}, {area.name}" if neighbourhood else area.name

    reports = _nearby_reports(
        area,
        centre,
        radius_km=radius_km,
        window_hours=REPORT_WINDOW_HOURS,
        now=now,
        user=user,
    )
    weather = _weather_section(area, now)
    rain = _rain_section(area, now)
    recent_rain = _recent_rain_section(area, now)
    waterlogging = _waterlogging_section(
        area, centre, resolution, reports, rain, recent_rain, now
    )
    heat = _heat_section(area, centre, now)
    air = _air_quality_section(centre, now)
    alerts = _alerts_section(area, neighbourhood, now)
    reports_section = _reports_section(area, centre, resolution, reports, user)
    status = _status_summary(
        waterlogging, heat, rain, air, alerts, reports_section, weather
    )

    reports_updated_at = (
        reports_section["results"][0]["occurred_at"] if reports_section.get("results") else None
    )
    modules = [
        {
            "key": "weather",
            "label": "Weather",
            "state": weather["state"],
            "updated_at": weather.get("retrieved_at"),
        },
        {
            "key": "waterlogging",
            "label": "Waterlogging signal",
            "state": waterlogging["state"],
            "updated_at": rain.get("retrieved_at"),
        },
        {
            "key": "alerts",
            "label": "Official alerts",
            "state": alerts["state"],
            "updated_at": alerts.get("last_success_at"),
        },
        {
            "key": "air_quality",
            "label": "Air quality",
            "state": air["state"],
            "updated_at": (air.get("measurement") or {}).get("measured_at"),
        },
        {
            "key": "heat",
            "label": "Heat",
            "state": heat["state"],
            "updated_at": heat["air"].get("retrieved_at"),
        },
        {
            "key": "reports",
            "label": "Community reports",
            "state": reports_section["state"],
            "updated_at": reports_updated_at,
        },
    ]
    available = sum(1 for module in modules if module["state"] == DataState.AVAILABLE)
    stale = sum(1 for module in modules if module["state"] == DataState.STALE)
    partial = sum(1 for module in modules if module["state"] == DataState.PARTIAL)
    unavailable = sum(1 for module in modules if module["state"] == DataState.UNAVAILABLE)
    confidence = "high" if available >= 5 else "medium" if available >= 3 else "low"
    status["confidence"] = confidence
    status["confidence_note"] = (
        f"{available} of {len(modules)} modules have a recent record; "
        f"{stale} stale, {partial} partial, {unavailable} unavailable. "
        "The headline is only as reliable as this coverage."
    )

    return {
        "generated_at": now,
        "method_version": PLACE_METHOD_VERSION,
        "place": {
            "area": {
                "slug": area.slug,
                "name": area.name,
                "centroid_lat": area.centroid_lat,
                "centroid_lon": area.centroid_lon,
            },
            "neighbourhood": (
                {
                    "slug": neighbourhood.slug,
                    "name": neighbourhood.name,
                    "latitude": neighbourhood.latitude,
                    "longitude": neighbourhood.longitude,
                }
                if neighbourhood
                else None
            ),
            "label": label,
            "resolution": resolution,
            "center": {"latitude": centre[0], "longitude": centre[1]},
            "scope_note": (
                f"Conditions are approximated from the area forecast point and public reports "
                f"within {radius_km} km. This is not a street-level sensor."
            ),
        },
        "status": status,
        "weather": weather,
        "rain": rain,
        "recent_rain": recent_rain,
        "waterlogging": waterlogging,
        "scorecard": place_scorecard(area, *centre) if neighbourhood else None,
        "heat": heat,
        "air_quality": air,
        "alerts": alerts,
        "reports": reports_section,
        "coverage": {
            "available": available,
            "stale": stale,
            "partial": partial,
            "unavailable": unavailable,
            "total": len(modules),
            "confidence": confidence,
            "modules": modules,
        },
        "disclaimer": (
            "This is decision support assembled from stored records. It is not an official "
            "warning service, and the waterlogging signal is rule-based, not a trained model."
        ),
    }
