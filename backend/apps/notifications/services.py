"""Turns forecasts, official alerts and reports into personal notifications.

Each event notifies a person once. In-app notifications always work; Telegram is an
optional extra delivery channel that needs TELEGRAM_BOT_TOKEN.
"""

from __future__ import annotations

import logging
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
from apps.core.geometry import haversine_m
from apps.incidents.models import IncidentCategory
from apps.incidents.services import live_reports
from apps.intelligence.place_status import _alert_scope
from apps.intelligence.today import (
    HEAT_INDEX_DANGER_C,
    HEAVY_RAIN_SOON_MM,
    heat_index_c,
    rain_soon,
)
from apps.locations.models import Area
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
        if _alert_scope(alert, area, None):
            events.append(
                {
                    "kind": NotificationKind.OFFICIAL_ALERT,
                    "title": f"Official warning: {alert.get_hazard_display()}",
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
    area = Area.objects.filter(is_active=True).order_by("name").first()
    created = 0
    if area is None:
        return {"created": 0, "users": 0}

    city_events = _city_events(area, now)
    reports = [report for report in live_reports(area, now=now) if report.category in NOTIFY_CATEGORIES]
    # Accounts made outside sign-up, such as admins, have no preference row yet.
    for user in get_user_model().objects.filter(is_active=True, preferences__isnull=True):
        UserPreference.objects.get_or_create(user=user)
    preferences = UserPreference.objects.filter(alerts_enabled=True, user__is_active=True).select_related("user")

    for preference in preferences:
        user = preference.user
        for event in city_events:
            created += int(_notify(preference, **event))

        for route in SavedRoute.objects.filter(user=user):
            for report, distance in reports_on_route(route, area, now=now):
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
