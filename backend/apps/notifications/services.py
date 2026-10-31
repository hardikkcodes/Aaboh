"""Turns forecasts, official alerts and reports into personal notifications.

Each event notifies a person once. In-app notifications always work; Telegram is an
optional extra delivery channel that needs TELEGRAM_BOT_TOKEN.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import SavedLocation, SavedRoute, UserPreference
from apps.accounts.routes import reports_on_route
from apps.alerts.models import AlertStatus, OfficialAlert
from apps.alerts.services import AlertMatch
from apps.core.geometry import haversine_m
from apps.incidents.models import IncidentCategory
from apps.incidents.services import live_reports
from apps.intelligence.place_status import _alert_scope
from apps.intelligence.today import (
    HEAT_INDEX_DANGER_C,
    HEAVY_RAIN_SOON_MM,
    RAIN_LIKELY_MM,
    RAIN_LIKELY_PROBABILITY,
    heat_index_c,
    rain_soon,
)
from apps.locations.models import Area
from apps.locations.services.regions import area_for_point, reporting_areas
from apps.weather.selectors import hourly_records

from .models import Notification, NotificationKind

logger = logging.getLogger("apps.notifications")
IST = ZoneInfo("Asia/Kolkata")
PLACE_RADIUS_M = 500
NOTIFY_CATEGORIES = {
    IncidentCategory.WATERLOGGING,
    IncidentCategory.FLOODING,
    IncidentCategory.FALLEN_TREE,
    IncidentCategory.ROAD_DISRUPTION,
    IncidentCategory.TRANSPORT_DISRUPTION,
}
QUIET_HOURS = {22, 23, 0, 1, 2, 3, 4, 5}
TELEGRAM_TIMEOUT_SECONDS = 15
NUDGE_LEAD = timedelta(hours=2)
NUDGE_RAIN_WINDOW = timedelta(hours=1)


def _notify(preference: UserPreference, *, kind: str, title: str, body: str, link: str, key: str) -> bool:
    if Notification.objects.filter(user=preference.user, dedupe_key=key).exists():
        return False
    try:
        with transaction.atomic():
            notification = Notification.objects.create(
                user=preference.user,
                kind=kind,
                title=title[:200],
                body=body[:500],
                link=link,
                dedupe_key=key,
            )
    except IntegrityError:
        return False
    deliver_telegram(notification, preference)
    return True


def deliver_telegram(notification: Notification, preference: UserPreference) -> bool:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or not preference.telegram_chat_id:
        return False
    local_hour = timezone.now().astimezone(IST).hour
    is_official = notification.kind == NotificationKind.OFFICIAL_ALERT
    if preference.quiet_hours and local_hour in QUIET_HOURS and not is_official:
        return False
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": preference.telegram_chat_id,
                "text": f"{notification.title}\n{notification.body}",
            },
            timeout=TELEGRAM_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        # The exception text contains the URL, which carries the bot token.
        logger.warning("Telegram delivery failed: %s", type(exc).__name__)
        return False
    if response.status_code != 200:
        logger.warning("Telegram delivery returned HTTP %s", response.status_code)
        return False
    notification.delivered_at = timezone.now()
    notification.save(update_fields=["delivered_at"])
    return True


def commute_nudge(leave_at, hours: list, now) -> str | None:
    """The rain hour to warn about, once a saved leaving time is close."""
    local = now.astimezone(IST)
    leaving = local.replace(hour=leave_at.hour, minute=leave_at.minute, second=0, microsecond=0)
    if not timedelta(0) <= leaving - local <= NUDGE_LEAD:
        return None
    for record in hours:
        if abs(record.valid_time - leaving) > NUDGE_RAIN_WINDOW:
            continue
        if (record.precipitation_probability or 0) >= RAIN_LIKELY_PROBABILITY or (
            record.precipitation_mm or 0
        ) >= RAIN_LIKELY_MM:
            return f"{record.valid_time.astimezone(IST):%H:%M}"
    return None


def _describe(report) -> str:
    place = report.address_text or (report.neighbourhood.name if report.neighbourhood else "")
    details = report.get_water_depth_display() or report.get_passability_display()
    return " · ".join(part for part in (place, details) if part)


def _city_events(area: Area, now) -> list[dict]:
    events = []
    alerts = (
        OfficialAlert.objects.filter(status=AlertStatus.ACTIVE)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .order_by("-issued_at")
    )
    for alert in alerts:
        match = _alert_scope(alert, area, None)
        if match:
            events.append(
                {
                    "kind": NotificationKind.OFFICIAL_ALERT,
                    "title": f"Official warning{' may include ' + area.name if match == AlertMatch.STATE else ''}: {alert.get_hazard_display()}",
                    "body": alert.title,
                    "link": "/alerts",
                    "key": f"alert:{alert.id}",
                }
            )

    hours = [record for record in hourly_records(area.slug, hours=24) if record.valid_time >= now]
    rain = rain_soon(hours, now)
    local = now.astimezone(IST)
    if rain["total_mm"] is not None and rain["total_mm"] >= HEAVY_RAIN_SOON_MM:
        events.append(
            {
                "kind": NotificationKind.HEAVY_RAIN,
                "title": "Heavy rain is forecast soon",
                "body": f"About {rain['total_mm']} mm in the next 2 hours (city-wide forecast).",
                "link": "/live",
                "key": f"rain:{local:%Y-%m-%d}:{local.hour // 3}",
            }
        )
    indices = [
        index
        for index in (heat_index_c(record.temperature_c, record.relative_humidity) for record in hours)
        if index is not None
    ]
    if indices and max(indices) >= HEAT_INDEX_DANGER_C:
        events.append(
            {
                "kind": NotificationKind.HEAT,
                "title": "Dangerous heat is forecast",
                "body": f"Feels like up to {max(indices)}°C. Avoid midday effort and drink water.",
                "link": "/",
                "key": f"heat:{local:%Y-%m-%d}",
            }
        )
    return events


def evaluate_alerts(*, now=None) -> dict:
    now = now or timezone.now()
    areas = list(reporting_areas())
    created = 0
    if not areas:
        return {"created": 0, "users": 0}

    area_events = {area.id: _city_events(area, now) for area in areas}
    reports = [
        report
        for area in areas
        for report in live_reports(area, now=now)
        if report.category in NOTIFY_CATEGORIES
    ]
    # Accounts made outside sign-up, such as admins, have no preference row yet.
    for user in get_user_model().objects.filter(is_active=True, preferences__isnull=True):
        UserPreference.objects.get_or_create(user=user)
    preferences = UserPreference.objects.filter(alerts_enabled=True, user__is_active=True).select_related(
        "user", "default_area"
    )

    for preference in preferences:
        user = preference.user
        home = preference.default_area.data_area if preference.default_area else areas[0]
        for event in area_events.get(home.id, []):
            created += int(_notify(preference, **event))

        for route in SavedRoute.objects.filter(user=user):
            latitude, longitude = route.points[0]
            route_area = area_for_point(latitude, longitude) or home
            if route.leave_at:
                hours = [item for item in hourly_records(route_area.slug, hours=6) if item.valid_time >= now]
                rain_time = commute_nudge(route.leave_at, hours, now)
                if rain_time:
                    created += int(
                        _notify(
                            preference,
                            kind=NotificationKind.ROUTE_RAIN,
                            title=f"Rain likely near your {route.label} trip",
                            body=f"Forecast around {rain_time}. You usually leave at {route.leave_at:%H:%M}, so consider leaving earlier.",
                            link="/routes",
                            key=f"route-rain:{route.id}:{now.astimezone(IST):%Y-%m-%d}",
                        )
                    )
            for report, distance in reports_on_route(route, route_area, now=now):
                if report.reporter_id == user.id or report.category not in NOTIFY_CATEGORIES:
                    continue
                created += int(
                    _notify(
                        preference,
                        kind=NotificationKind.ROUTE_REPORT,
                        title=f"{report.get_category_display()} on {route.label}",
                        body=f"{_describe(report)} · about {distance} m from your route",
                        link=f"/reports/{report.id}",
                        key=f"report:{report.id}",
                    )
                )

        for place in SavedLocation.objects.filter(user=user):
            for report in reports:
                if report.reporter_id == user.id:
                    continue
                if haversine_m(place.latitude, place.longitude, report.latitude, report.longitude) > PLACE_RADIUS_M:
                    continue
                created += int(
                    _notify(
                        preference,
                        kind=NotificationKind.PLACE_REPORT,
                        title=f"{report.get_category_display()} near {place.label}",
                        body=_describe(report),
                        link=f"/reports/{report.id}",
                        key=f"report:{report.id}",
                    )
                )
    return {"created": created, "users": preferences.count()}
