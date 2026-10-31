"""Private route checks: active resident reports close to a saved corridor."""

from __future__ import annotations

from datetime import timedelta
from zoneinfo import ZoneInfo

from django.db.models import Q
from django.utils import timezone
from shapely.geometry import LineString

from apps.alerts.models import AlertStatus, OfficialAlert
from apps.core.geometry import point_geojson, project_to_utm
from apps.incidents.models import Passability, WaterDepth
from apps.incidents.services import live_reports
from apps.intelligence.place_status import _alert_scope
from apps.intelligence.today import rain_soon
from apps.locations.models import Area
from apps.locations.services.regions import area_for_point, reporting_areas
from apps.rainfall.outlook import chance_at
from apps.weather.selectors import hourly_records

from .models import SavedRoute

IST = ZoneInfo("Asia/Kolkata")
ROUTE_BUFFER_M = 300
BLOCKING_DEPTHS = {WaterDepth.WAIST, WaterDepth.ABOVE_WAIST}


def route_line(route: SavedRoute) -> LineString:
    """The corridor in metres (UTM), so distances can be measured directly."""
    coordinates = [[longitude, latitude] for latitude, longitude in route.points]
    return project_to_utm({"type": "LineString", "coordinates": coordinates})


def reports_on_route(route: SavedRoute, area: Area, *, now=None) -> list:
    line = route_line(route)
    matches = []
    for report in live_reports(area, now=now):
        distance = line.distance(project_to_utm(point_geojson(report.latitude, report.longitude)))
        if distance <= ROUTE_BUFFER_M:
            matches.append((report, round(distance)))
    return matches


def route_status(route: SavedRoute, *, now=None) -> dict:
    now = now or timezone.now()
    latitude, longitude = route.points[0]
    area = area_for_point(latitude, longitude) or reporting_areas().first()
    matches = reports_on_route(route, area, now=now) if area else []
    blocked = any(
        report.passability == Passability.NONE or report.water_depth in BLOCKING_DEPTHS
        for report, _ in matches
    )
    hours = [record for record in hourly_records(area.slug, hours=3) if record.valid_time >= now] if area else []
    alerts = OfficialAlert.objects.filter(status=AlertStatus.ACTIVE).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )
    official = sum(1 for alert in alerts if area and _alert_scope(alert, area, None))

    if blocked:
        summary = "serious_reports"
    elif matches:
        summary = "reports"
    else:
        summary = "no_reports"
    leaving = None
    if route.leave_at:
        local = now.astimezone(IST)
        leaving = local.replace(hour=route.leave_at.hour, minute=route.leave_at.minute, second=0, microsecond=0)
        if leaving < local:
            leaving += timedelta(days=1)
    return {
        "route": {"id": str(route.id), "label": route.label, "points": route.points},
        "checked_at": now,
        "distance_km": round(route_line(route).length / 1000, 1),
        "rain_chance_now_pct": chance_at(area, now) if area else None,
        "leave_at": route.leave_at,
        "rain_chance_leaving_pct": chance_at(area, leaving) if area and leaving else None,
        "summary": summary,
        "buffer_m": ROUTE_BUFFER_M,
        "official_alerts": official,
        "rain": rain_soon(hours, now),
        "reports": [
            {
                "id": str(report.id),
                "category_label": report.get_category_display(),
                "place": report.address_text or (report.neighbourhood.name if report.neighbourhood else ""),
                "water_depth_label": report.get_water_depth_display(),
                "passability_label": report.get_passability_display(),
                "trust": report.trust,
                "occurred_at": report.occurred_at,
                "distance_m": distance,
            }
            for report, distance in matches
        ],
        "note": "Only reports close to the line you drew. No report does not mean the road is clear.",
    }
