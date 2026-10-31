"""Deterministic, evidence-backed local guidance.

Rules never invent an observation: every insight is derived from a stored record
and carries the source, timestamp, units and quality status of that record; a
rule does not fire when its input data is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from statistics import mean, median
from typing import Any

from django.db.models import Q
from django.utils import timezone

from apps.air_quality.models import AQIStation
from apps.alerts.models import AlertStatus, OfficialAlert
from apps.alerts.services import alert_match
from apps.core.geometry import haversine_m, parse_geometry
from apps.core.models import DataSource
from apps.core.quality import DataState, source_availability
from apps.core.serializers import source_summary
from apps.environment.models import EnvironmentalObservation
from apps.incidents.models import IncidentCategory, IncidentReport, IncidentStatus
from apps.locations.models import Area
from apps.weather.models import WeatherKind, WeatherRecord

RULESET_VERSION = "1.0"
HOT_APPARENT_C = {"info": 35.0, "caution": 38.0, "warning": 40.0}
RAIN_24H_MM = {"info": 5.0, "caution": 20.0, "warning": 50.0}
AQI_STATION = {"info": 100, "caution": 200, "warning": 300}
LST_P90_C = {"info": 38.0, "caution": 42.0, "warning": 45.0}
CLIMATE_ANOMALY_C = {"info": 0.5, "caution": 1.0}
NEARBY_STATION_KM = 75.0


@dataclass
class RuleContext:
    area: Area
    now: Any
    current: WeatherRecord | None
    hourly: list[WeatherRecord]
    daily: list[WeatherRecord]
    alerts: list[OfficialAlert]
    nearest_station: AQIStation | None
    station_measurement: Any | None
    stations_reporting: int
    verified_incidents: list[IncidentReport]
    unverified_incidents: list[IncidentReport]
    latest_lst_date: Any | None
    lst_values: list[float]
    climate_metrics: list[Any]
    sources: dict[str, DataSource] = field(default_factory=dict)

    def source(self, slug: str) -> DataSource | None:
        return self.sources.get(slug)


def _source_map() -> dict[str, DataSource]:
    return {source.slug: source for source in DataSource.objects.filter(is_active=True)}


def _evidence(
    *,
    evidence_type: str,
    label: str,
    source: DataSource | None,
    observed_at=None,
    reference: dict | None = None,
    source_url: str = "",
    quality_status: str = DataState.AVAILABLE,
    dataset: str = "",
) -> dict:
    return {
        "evidence_type": evidence_type,
        "label": label,
        "source": source_summary(source, dataset=dataset) if source else {},
        "observed_at": observed_at,
        "reference": reference or {},
        "source_url": source_url,
        "quality_status": quality_status,
    }


def _max_severity(candidates: list[str]) -> str:
    order = {"info": 0, "caution": 1, "warning": 2}
    return max(candidates, key=lambda value: order.get(value, 0), default="info")


def _insight(
    *,
    rule_id: str,
    kind: str,
    title: str,
    body: str,
    severity: str,
    evidence: list[dict],
    caveats: list[str] | None = None,
    valid_from=None,
    valid_until=None,
) -> dict:
    return {
        "rule_id": rule_id,
        "kind": kind,
        "title": title,
        "body": body,
        "severity": severity,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "evidence": evidence,
        "caveats": caveats or [],
    }


def _build_context(area: Area, now) -> RuleContext:
    sources = _source_map()

    current = (
        WeatherRecord.objects.filter(
            location__area=area, source__slug="open_meteo", kind=WeatherKind.CURRENT
        )
        .select_related("source", "location")
        .order_by("-retrieved_at")
        .first()
    )
    hourly = list(
        WeatherRecord.objects.filter(
            location__area=area,
            source__slug="open_meteo",
            kind=WeatherKind.HOURLY,
            valid_time__gte=now - timedelta(minutes=30),
            valid_time__lte=now + timedelta(hours=24),
        )
        .select_related("source")
        .order_by("valid_time")
    )
    daily = list(
        WeatherRecord.objects.filter(
            location__area=area,
            source__slug="open_meteo",
            kind=WeatherKind.DAILY,
            valid_time__gte=now - timedelta(days=1),
            valid_time__lte=now + timedelta(days=2),
        )
        .select_related("source")
        .order_by("valid_time")
    )

    alerts = list(
        OfficialAlert.objects.filter(status=AlertStatus.ACTIVE)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .select_related("source")
        .order_by("-issued_at")
    )
    alerts = [alert for alert in alerts if alert_match(alert, area)]

    stations = list(AQIStation.objects.filter(is_active=True).select_related("source"))
    nearest_station = None
    nearest_distance = None
    for station in stations:
        distance = haversine_m(*area.focus, station.latitude, station.longitude)
        if distance > NEARBY_STATION_KM * 1000:
            continue
        if nearest_distance is None or distance < nearest_distance:
            nearest_distance, nearest_station = distance, station
    station_measurement = None
    stations_reporting = 0
    if nearest_station is not None:
        station_measurement = (
            nearest_station.measurements.filter(measured_at__gte=now - timedelta(hours=24))
            .order_by("-measured_at")
            .first()
        )
        stations_reporting = (
            AQIStation.objects.filter(is_active=True)
            .filter(measurements__measured_at__gte=now - timedelta(hours=24))
            .distinct()
            .count()
        )

    verified_incidents = list(
        IncidentReport.objects.filter(
            area=area.data_area,
            is_public=True,
            cleared_at__isnull=True,
            status=IncidentStatus.VERIFIED,
            occurred_at__gte=now - timedelta(hours=12),
        )
        .exclude(category=IncidentCategory.OTHER)
        .select_related("neighbourhood", "source")
        .order_by("-occurred_at")[:20]
    )
    unverified_incidents = list(
        IncidentReport.objects.filter(
            area=area.data_area,
            is_public=True,
            cleared_at__isnull=True,
            status__in=[IncidentStatus.SUBMITTED, IncidentStatus.UNDER_REVIEW],
            occurred_at__gte=now - timedelta(hours=6),
        )
        .select_related("source")
        .order_by("-created_at")[:20]
    )

    lst_qs = EnvironmentalObservation.objects.filter(cell__area=area.data_area, lst_c__isnull=False)
    latest_lst_date = lst_qs.order_by("-observed_on").values_list("observed_on", flat=True).first()
    lst_values = (
        list(lst_qs.filter(observed_on=latest_lst_date).values_list("lst_c", flat=True))
        if latest_lst_date
        else []
    )

    climate_metrics = list(
        area.data_area.climate_metrics.filter(variable="temperature_2m_mean", period_type="annual")
        .select_related("baseline", "source")
        .order_by("period_start")
    )

    return RuleContext(
        area=area,
        now=now,
        current=current,
        hourly=hourly,
        daily=daily,
        alerts=alerts,
        nearest_station=nearest_station,
        station_measurement=station_measurement,
        stations_reporting=stations_reporting,
        verified_incidents=verified_incidents,
        unverified_incidents=unverified_incidents,
        latest_lst_date=latest_lst_date,
        lst_values=lst_values,
        climate_metrics=climate_metrics,
        sources=sources,
    )


def _module_availability(source, *, data_present: bool, missing_reason: str, extra_reason: str | None = None) -> dict:
    availability = source_availability(source) if source else {"state": DataState.UNAVAILABLE}
    if data_present:
        state = availability["state"]
        if state in {DataState.UNAVAILABLE, DataState.INVALID}:
            state = DataState.STALE
    else:
        state = DataState.UNAVAILABLE
    reason = extra_reason
    if state == DataState.UNAVAILABLE:
        reason = missing_reason
    return {"module": "", "state": state, "reason": reason}


def _availability_items(ctx: RuleContext) -> list[dict]:
    """Per-module input availability for the briefing, with honest reasons."""
    items = []

    weather = _module_availability(
        ctx.source("open_meteo"),
        data_present=bool(ctx.current or ctx.hourly),
        missing_reason="No weather forecast has been ingested for this area. Run fetch_weather.",
        extra_reason=None if ctx.current else "Only forecast hours are available; no current observation.",
    )
    weather["module"] = "weather"
    items.append(weather)

    alerts_source = ctx.source("sachet") or ctx.source("imd")
    alerts_availability = source_availability(alerts_source) if alerts_source else {"state": DataState.UNAVAILABLE}
    alerts_healthy = alerts_availability["state"] in {DataState.AVAILABLE, DataState.PARTIAL}
    if alerts_healthy:
        alerts_state = alerts_availability["state"]
        alerts_reason = (
            None
            if ctx.alerts
            else "The official alert feed is reachable. No active warning covers this area right now."
        )
    elif ctx.alerts:
        alerts_state = DataState.STALE
        alerts_reason = "The latest official alert-feed refresh failed; stored warnings may be stale."
    else:
        alerts_state = DataState.UNAVAILABLE
        alerts_reason = "No official alert feed has been ingested. Run fetch_alerts."
    items.append({"module": "alerts", "state": alerts_state, "reason": alerts_reason})

    air = _module_availability(
        ctx.source("cpcb"),
        data_present=ctx.station_measurement is not None,
        missing_reason=(
            "No CPCB station measurement within 24 hours of this area. Run fetch_cpcb."
            if ctx.nearest_station is None
            else f"The nearest CPCB station ({ctx.nearest_station.name}) has no measurement in the last 24 hours."
        ),
    )
    air["module"] = "air_quality"
    items.append(air)

    environment = _module_availability(
        ctx.source("landsat"),
        data_present=bool(ctx.latest_lst_date and ctx.lst_values),
        missing_reason="No Landsat land-surface temperature observations have been ingested.",
    )
    environment["module"] = "environment"
    items.append(environment)

    climate = _module_availability(
        ctx.source("era5_land"),
        data_present=bool(ctx.climate_metrics),
        missing_reason="No ERA5-Land annual climate metrics have been ingested. Run fetch_climate.",
    )
    climate["module"] = "climate"
    items.append(climate)

    community_source = ctx.source("community_reports")
    community_count = len(ctx.verified_incidents) + len(ctx.unverified_incidents)
    items.append(
        {
            "module": "community",
            "state": DataState.AVAILABLE if community_source else DataState.UNAVAILABLE,
            "reason": (
                "No public community reports fall inside the current rule windows."
                if not community_count
                else None
            ),
        }
    )
    return items


def _alert_scope(alert: OfficialAlert, area: Area) -> bool:
    """True only when the alert geometry demonstrably intersects the area."""
    if not alert.geometry or not area.boundary:
        return False
    try:
        return parse_geometry(alert.geometry).intersects(parse_geometry(area.boundary))
    except ValueError:
        return False


def _official_alert_rule(ctx: RuleContext) -> dict | None:
    if not ctx.alerts:
        return None
    worst = "caution"
    evidence = []
    for alert in ctx.alerts[:4]:
        matches = _alert_scope(alert, ctx.area)
        evidence.append(
            _evidence(
                evidence_type="official_warning",
                label=f"{alert.get_hazard_display()} — {alert.severity.title()}",
                source=alert.source,
                observed_at=alert.issued_at,
                reference={
                    "alert_id": str(alert.id),
                    "external_id": alert.external_id,
                    "severity": alert.severity,
                    "status": alert.status,
                    "areas_text": alert.areas_text,
                    "geometry_intersects_area": matches,
                    "expires_at": alert.expires_at,
                },
                source_url=alert.source_url,
                quality_status=alert.quality_status,
            )
        )
        if alert.severity in {"severe", "extreme"}:
            worst = "warning"
        elif alert.severity == "moderate" and worst != "warning":
            worst = "caution"
    titles = ", ".join(alert.get_hazard_display() for alert in ctx.alerts[:3])
    return _insight(
        rule_id="official_alert_active",
        kind="official_warning",
        title=f"Official warning in effect: {titles}",
        body=(
            f"{len(ctx.alerts)} active official warning(s) are published by the source. "
            "Read the original bulletin before changing plans; this platform does not re-issue warnings."
        ),
        severity=worst,
        evidence=evidence,
        caveats=[
            "Official warnings can cover districts larger than a neighbourhood; check the original bulletin.",
            "Absence of a warning does not mean conditions are safe.",
        ],
        valid_from=ctx.alerts[0].effective_at or ctx.alerts[0].issued_at,
        valid_until=max((a.expires_at for a in ctx.alerts if a.expires_at), default=None),
    )


def _heat_rule(ctx: RuleContext) -> dict | None:
    record = ctx.current
    value = None
    label = ""
    if record and record.apparent_temperature_c is not None:
        value, label = record.apparent_temperature_c, "apparent temperature"
    elif record and record.temperature_c is not None:
        value, label = record.temperature_c, "air temperature"
    else:
        daily = next(
            (day for day in ctx.daily if day.temperature_max_c is not None),
            None,
        )
        if daily is None:
            return None
        value, label, record = daily.temperature_max_c, "forecast daily maximum temperature", daily
    if value is None or value < HOT_APPARENT_C["info"]:
        return None
    severity = "info"
    if value >= HOT_APPARENT_C["warning"]:
        severity = "warning"
    elif value >= HOT_APPARENT_C["caution"]:
        severity = "caution"
    return _insight(
        rule_id="heat_stress",
        kind="heat",
        title=f"Heat stress: {label} {value:.1f}°C",
        body=(
            "Drink water, avoid strenuous activity during the afternoon and check on neighbours "
            "who are older, unwell or living in poorly ventilated housing."
        ),
        severity=severity,
        evidence=[
            _evidence(
                evidence_type="forecast" if record.is_forecast else "observation",
                label=f"Open-Meteo {label}",
                source=record.source,
                observed_at=record.valid_time,
                reference={
                    "weather_record_id": str(record.id),
                    "kind": record.kind,
                    "value_c": value,
                    "apparent_temperature_c": record.apparent_temperature_c,
                    "temperature_c": record.temperature_c,
                    "retrieved_at": record.retrieved_at,
                },
                dataset="Open-Meteo forecast",
            )
        ],
        caveats=[
            "Provider forecast values are not official warnings or station measurements.",
            "Heat stress depends on humidity, ventilation and personal health.",
        ],
        valid_from=record.valid_time,
    )


def _rain_rule(ctx: RuleContext) -> dict | None:
    if not ctx.hourly:
        return None
    window = [r for r in ctx.hourly if r.valid_time >= ctx.now]
    if not window:
        return None
    total = sum((r.precipitation_mm or 0.0) for r in window)
    if total < RAIN_24H_MM["info"]:
        return None
    max_probability = max((r.precipitation_probability or 0.0) for r in window)
    severity = "info"
    if total >= RAIN_24H_MM["warning"]:
        severity = "warning"
    elif total >= RAIN_24H_MM["caution"]:
        severity = "caution"
    peak = max(window, key=lambda r: r.precipitation_mm or 0.0)
    return _insight(
        rule_id="rain_next_24h",
        kind="rainfall",
        title=f"Rain expected: about {total:.1f} mm in the next 24 hours",
        body=(
            "Carry rain protection, allow extra travel time and avoid waterlogged underpasses. "
            "This is a weather forecast, not a flood or waterlogging prediction."
        ),
        severity=severity,
        evidence=[
            _evidence(
                evidence_type="forecast",
                label="Open-Meteo hourly precipitation forecast",
                source=window[0].source,
                observed_at=window[0].valid_time,
                reference={
                    "window_start": window[0].valid_time,
                    "window_end": window[-1].valid_time,
                    "total_mm": round(total, 2),
                    "max_hourly_mm": peak.precipitation_mm,
                    "max_probability_pct": max_probability,
                    "hours": len(window),
                },
                dataset="Open-Meteo forecast",
            )
        ],
        caveats=[
            "Forecast rainfall is not an official warning and does not by itself predict local flooding.",
            "Check community reports and official alerts as separate evidence.",
        ],
        valid_from=window[0].valid_time,
        valid_until=window[-1].valid_time,
    )


def _air_quality_rule(ctx: RuleContext) -> dict | None:
    measurement = ctx.station_measurement
    if measurement is None or measurement.aqi is None:
        return None
    aqi = measurement.aqi
    if aqi < AQI_STATION["info"]:
        return None
    severity = "info"
    if aqi >= AQI_STATION["warning"]:
        severity = "warning"
    elif aqi >= AQI_STATION["caution"]:
        severity = "caution"
    station = ctx.nearest_station
    return _insight(
        rule_id="air_quality_station",
        kind="air_quality",
        title=f"Air quality at {station.name}: AQI {aqi}",
        body=(
            f"The nearest reporting station ({station.name}) measured AQI {aqi}"
            f"{' (' + measurement.aqi_category + ')' if measurement.aqi_category else ''}. "
            "Sensitive groups may wish to reduce prolonged outdoor exertion."
        ),
        severity=severity,
        evidence=[
            _evidence(
                evidence_type="station_measurement",
                label=f"CPCB station measurement — {station.name}",
                source=measurement.source,
                observed_at=measurement.measured_at,
                reference={
                    "station_id": str(station.id),
                    "station_name": station.name,
                    "distance_km": round(
                        haversine_m(
                            *ctx.area.focus,
                            station.latitude,
                            station.longitude,
                        )
                        / 1000,
                        2,
                    ),
                    "aqi": aqi,
                    "category": measurement.aqi_category,
                    "pm25": measurement.pm25,
                    "pm10": measurement.pm10,
                    "stations_reporting": ctx.stations_reporting,
                },
                dataset="CPCB station data",
            )
        ],
        caveats=[
            "This is one monitoring station, not a neighbourhood-wide AQI surface.",
            "Station values may be stale or provisional; check the measurement time.",
        ],
        valid_from=measurement.measured_at,
        valid_until=measurement.measured_at + timedelta(hours=24),
    )


def _incident_rule(ctx: RuleContext) -> dict | None:
    water_categories = {
        IncidentCategory.WATERLOGGING,
        IncidentCategory.FLOODING,
        IncidentCategory.BLOCKED_DRAINAGE,
    }
    water = [item for item in ctx.verified_incidents if item.category in water_categories]
    if not water:
        return None
    severity = "caution" if len(water) < 3 else "warning"
    evidence = [
        _evidence(
            evidence_type="community_report",
            label=f"Verified community report: {item.get_category_display()}",
            source=item.source,
            observed_at=item.occurred_at,
            reference={
                "incident_id": str(item.id),
                "category": item.category,
                "status": item.status,
                "verified_at": item.verified_at,
                "neighbourhood": item.neighbourhood.name if item.neighbourhood else None,
                "latitude": round(item.latitude, 5),
                "longitude": round(item.longitude, 5),
            },
            quality_status=DataState.AVAILABLE,
        )
        for item in water[:5]
    ]
    return _insight(
        rule_id="verified_waterlogging",
        kind="waterlogging",
        title=f"{len(water)} verified waterlogging report(s) in the last 12 hours",
        body=(
            "Recent resident reports have been checked by a moderator. Avoid the reported locations "
            "where possible and never walk or drive through standing water."
        ),
        severity=severity,
        evidence=evidence,
        caveats=[
            "Community reports describe individual locations and are not a flood forecast.",
            "Conditions can change quickly; a location not reported may still be affected.",
        ],
        valid_from=min(item.occurred_at for item in water),
    )


def _unverified_incident_rule(ctx: RuleContext) -> dict | None:
    if not ctx.unverified_incidents:
        return None
    evidence = [
        _evidence(
            evidence_type="community_report",
            label=f"Unverified community report: {item.get_category_display()}",
            source=item.source,
            observed_at=item.occurred_at,
            reference={
                "incident_id": str(item.id),
                "category": item.category,
                "status": item.status,
                "latitude": round(item.latitude, 5),
                "longitude": round(item.longitude, 5),
            },
            quality_status=DataState.PARTIAL,
        )
        for item in ctx.unverified_incidents[:5]
    ]
    return _insight(
        rule_id="unverified_reports_recent",
        kind="community",
        title=f"{len(ctx.unverified_incidents)} new community report(s) awaiting review",
        body=(
            "These reports have not been verified. Treat them as unconfirmed signals and rely on "
            "official warnings and your own observation."
        ),
        severity="info",
        evidence=evidence,
        caveats=["Unverified reports may be mistaken, duplicated or outdated."],
    )


def _lst_rule(ctx: RuleContext) -> dict | None:
    if not ctx.lst_values:
        return None
    values = sorted(ctx.lst_values)
    p90 = values[min(len(values) - 1, int(round(0.9 * (len(values) - 1))))]
    med = median(values)
    if p90 < LST_P90_C["info"] and (p90 - med) < 3.0:
        return None
    severity = "info"
    if p90 >= LST_P90_C["warning"]:
        severity = "warning"
    elif p90 >= LST_P90_C["caution"]:
        severity = "caution"
    observation = (
        EnvironmentalObservation.objects.filter(
            cell__area=ctx.area.data_area, observed_on=ctx.latest_lst_date, lst_c__isnull=False
        )
        .select_related("scene", "scene__source")
        .order_by("-lst_c")
        .first()
    )
    return _insight(
        rule_id="satellite_lst_hotspots",
        kind="heat",
        title=f"Satellite land-surface hotspots: 90th percentile {p90:.1f}°C",
        body=(
            "Satellite thermal data shows hot surfaces on the latest cloud-free scene. "
            "Land-surface temperature is not air temperature; use it to compare places, not to "
            "decide whether it is safe to work outdoors."
        ),
        severity=severity,
        evidence=[
            _evidence(
                evidence_type="earth_observation",
                label="Landsat land-surface temperature aggregated to 1 km cells",
                source=observation.scene.source if observation else ctx.source("landsat"),
                observed_at=observation.scene.acquired_at if observation else None,
                reference={
                    "scene_id": observation.scene.scene_id if observation else None,
                    "observed_on": ctx.latest_lst_date,
                    "cells_with_data": len(values),
                    "median_c": round(med, 2),
                    "p90_c": round(p90, 2),
                    "hottest_cell": observation.cell.code if observation else None,
                    "hottest_cell_c": observation.lst_c if observation else None,
                },
                dataset="Landsat Collection 2 Level 2",
            )
        ],
        caveats=[
            "LST is a satellite-retrieved surface temperature, not measured air temperature.",
            "Cloud cover and the 16-day revisit cycle can make the latest scene several days old.",
        ],
        valid_from=observation.scene.acquired_at if observation else None,
    )


def _climate_rule(ctx: RuleContext) -> dict | None:
    metrics = [m for m in ctx.climate_metrics if m.value is not None]
    if not metrics:
        return None
    latest = metrics[-1]
    anomaly = latest.anomaly
    years = [m.period_start.year for m in metrics]
    values = [m.value for m in metrics]
    slope = None
    if len(metrics) >= 5:
        x_mean = mean(years)
        y_mean = mean(values)
        denominator = sum((year - x_mean) ** 2 for year in years)
        if denominator:
            slope = sum((year - x_mean) * (value - y_mean) for year, value in zip(years, values, strict=True)) / denominator
    if (anomaly is None or abs(anomaly) < CLIMATE_ANOMALY_C["info"]) and (
        slope is None or abs(slope * 10) < 0.15
    ):
        return None
    severity = "info"
    if anomaly is not None and abs(anomaly) >= CLIMATE_ANOMALY_C["caution"]:
        severity = "caution"
    direction = "above" if (anomaly or 0) >= 0 else "below"
    return _insight(
        rule_id="climate_annual_temperature",
        kind="climate",
        title=(
            f"{latest.period_start.year} annual mean was {latest.value:.1f}°C"
            + (f", {abs(anomaly):.1f}°C {direction} the baseline" if anomaly is not None else "")
        ),
        body=(
            "Long-term reanalysis data provides context for heat and rainfall. A single year is not "
            "proof of a trend, and these values are area-level rather than neighbourhood measurements."
        ),
        severity=severity,
        evidence=[
            _evidence(
                evidence_type="reanalysis",
                label=f"ERA5-Land annual mean temperature ({latest.period_start.year})",
                source=latest.source,
                observed_at=latest.period_end,
                reference={
                    "metric_id": str(latest.id),
                    "value_c": latest.value,
                    "anomaly_c": anomaly,
                    "baseline": latest.baseline.name if latest.baseline else None,
                    "baseline_value_c": latest.baseline.value if latest.baseline else None,
                    "slope_c_per_decade": round(slope * 10, 4) if slope is not None else None,
                    "complete_years": len(metrics),
                },
                dataset="ERA5-Land",
            )
        ],
        caveats=[
            "ERA5-Land has ~9 km native resolution and is a reanalysis, not a local station record.",
            "The trend is descriptive; short records and autocorrelation limit causal interpretation.",
        ],
    )


def _availability_rule(ctx: RuleContext) -> dict | None:
    checks = [
        ("official alerts", "sachet", "No official alert feed has been ingested. Run fetch_alerts."),
        ("station air quality", "cpcb", "No CPCB station measurement is available. Run fetch_cpcb."),
        (
            "satellite observations",
            "landsat",
            "No Landsat observations have been ingested; Earth Engine credentials may be missing.",
        ),
    ]
    missing = []
    evidence = []
    for label, slug, reason in checks:
        source = ctx.source(slug)
        if source is None:
            continue
        availability = source_availability(source)
        if availability["state"] not in {DataState.AVAILABLE, DataState.PARTIAL, DataState.PROCESSING}:
            missing.append(label)
            evidence.append(
                _evidence(
                    evidence_type="data_availability",
                    label=f"{label} — {availability['state']}",
                    source=source,
                    observed_at=availability.get("last_success_at"),
                    reference={
                        "state": availability["state"],
                        "last_attempt_at": availability.get("last_attempt_at"),
                        "reason": reason,
                    },
                    quality_status=availability["state"],
                )
            )
    if not missing:
        return None
    return _insight(
        rule_id="data_availability_caveat",
        kind="data_availability",
        title="Some data layers are unavailable",
        body=(
            "This briefing is deliberately incomplete: "
            + ", ".join(missing)
            + ". No substitute values have been generated."
        ),
        severity="info",
        evidence=evidence,
        caveats=["A missing layer means the platform has no verified data, not that conditions are safe."],
    )


def generate_insights(area: Area, *, now=None) -> dict:
    now = now or timezone.now()
    ctx = _build_context(area, now)
    candidates = [
        _official_alert_rule(ctx),
        _heat_rule(ctx),
        _rain_rule(ctx),
        _air_quality_rule(ctx),
        _incident_rule(ctx),
        _unverified_incident_rule(ctx),
        _lst_rule(ctx),
        _climate_rule(ctx),
        _availability_rule(ctx),
    ]
    insights = [item for item in candidates if item is not None]
    order = {"warning": 0, "caution": 1, "info": 2}
    insights.sort(key=lambda item: (order.get(item["severity"], 3), item["rule_id"]))
    substantive = [item for item in insights if item["kind"] != "data_availability"]
    return {
        "area": {"slug": area.slug, "name": area.name},
        "generated_at": now,
        "state": DataState.AVAILABLE if substantive else DataState.PARTIAL if insights else DataState.UNAVAILABLE,
        "count": len(insights),
        "ruleset_version": RULESET_VERSION,
        "insights": insights,
        "data_availability": _availability_items(ctx),
        "thresholds": {
            "hot_apparent_c": HOT_APPARENT_C,
            "rain_24h_mm": RAIN_24H_MM,
            "aqi_station": AQI_STATION,
            "lst_p90_c": LST_P90_C,
            "climate_anomaly_c": CLIMATE_ANOMALY_C,
        },
        "methodology": (
            "Rules run deterministically over stored observations, forecasts and reports. "
            "Each insight lists its evidence; rules do not fire when the required input is missing. "
            "Community reports and provider forecasts are never labelled as official warnings."
        ),
        "disclaimer": (
            "This is decision support, not an official warning service or medical advice. "
            "Always follow instructions from IMD, KMC and emergency services."
        ),
    }


def persist_insights(area: Area, insights: list[dict]) -> list:
    from .models import InsightSeverity, Recommendation, RecommendationEvidence

    valid_severities = {choice for choice, _ in InsightSeverity.choices}
    created = []
    for item in insights:
        severity = item["severity"] if item["severity"] in valid_severities else InsightSeverity.INFO
        recommendation = Recommendation.objects.create(
            area=area,
            rule_id=item["rule_id"],
            kind=item["kind"],
            title=item["title"],
            body=item["body"],
            severity=severity,
            valid_from=item.get("valid_from"),
            valid_until=item.get("valid_until"),
            metadata={"caveats": item.get("caveats", []), "ruleset_version": RULESET_VERSION},
        )
        for evidence in item.get("evidence", []):
            source_slug = (evidence.get("source") or {}).get("slug")
            RecommendationEvidence.objects.create(
                recommendation=recommendation,
                evidence_type=evidence["evidence_type"],
                label=evidence["label"],
                source=DataSource.objects.filter(slug=source_slug).first() if source_slug else None,
                observed_at=evidence.get("observed_at"),
                reference=evidence.get("reference", {}),
                source_url=evidence.get("source_url", ""),
                quality_status=evidence.get("quality_status", DataState.AVAILABLE),
            )
        created.append(recommendation)
    return created
