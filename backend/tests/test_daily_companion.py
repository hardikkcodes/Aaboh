"""Today brief, week planner, saved routes, personal alerts and impact."""

from __future__ import annotations

from datetime import timedelta
from unittest import mock

import pytest
import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import SavedLocation, SavedRoute, UserPreference
from apps.alerts.models import OfficialAlert
from apps.core.geometry import point_geojson
from apps.core.models import DataSource
from apps.incidents.services import create_incident
from apps.intelligence.today import best_outdoor_window, build_today, heat_index_c, rain_soon
from apps.notifications.models import Notification
from apps.notifications.services import deliver_telegram, evaluate_alerts
from apps.weather.models import WeatherLocation, WeatherRecord

pytestmark = pytest.mark.django_db
ROUTE_POINTS = [[22.55, 88.35], [22.56, 88.35]]


@pytest.fixture(autouse=True)
def clear_rate_limits():
    cache.clear()
    yield
    cache.clear()


def forecast(area, rows: list[dict]) -> None:
    source = DataSource.objects.get(slug="open_meteo")
    location = WeatherLocation.objects.create(
        area=area,
        name="Forecast point",
        point=point_geojson(22.56, 88.36),
        latitude=22.56,
        longitude=88.36,
        source=source,
        provider_location_key="test",
    )
    now = timezone.now()
    for offset, row in enumerate(rows, start=1):
        WeatherRecord.objects.create(
            location=location,
            source=source,
            kind="HOURLY",
            valid_time=now + timedelta(hours=offset),
            retrieved_at=now,
            **row,
        )


def report(area, reporter=None, *, latitude=22.555, longitude=88.3505, **extra):
    return create_incident(
        reporter=reporter,
        area=area,
        category=extra.pop("category", "waterlogging"),
        occurred_at=timezone.now() - timedelta(minutes=10),
        latitude=latitude,
        longitude=longitude,
        **extra,
    )


def other_user():
    return get_user_model().objects.create_user(
        username="other", email="other@example.com", password="a-very-long-password-123"
    )


def test_heat_index_rises_with_humidity():
    assert heat_index_c(34, 80) > heat_index_c(34, 40)
    assert heat_index_c(20, 90) == 20
    assert heat_index_c(None, 50) is None


def test_missing_forecast_is_unknown_not_zero(area):
    today = build_today(area)
    assert today["state"] == "UNAVAILABLE"
    assert today["rain"]["total_mm"] is None
    assert today["heat"]["level"] == "unknown"
    assert today["best_outdoor_window"] is None


def test_today_warns_of_heavy_rain_and_nearby_reports(api_client, area):
    forecast(area, [{"temperature_c": 30, "relative_humidity": 70, "precipitation_mm": 8, "precipitation_probability": 90}] * 3)
    report(area, latitude=22.558, longitude=88.359)

    body = api_client.get("/api/v1/today/", {"area": area.slug}).json()

    assert body["state"] == "AVAILABLE"
    assert {"heavy_rain_soon", "reports_nearby"} <= {tip["key"] for tip in body["tips"]}
    assert "safe" not in " ".join(tip["text"] for tip in body["tips"]).lower()


def test_rain_soon_only_counts_the_next_two_hours(area):
    now = timezone.now()
    rows = [
        WeatherRecord(valid_time=now + timedelta(hours=hour), precipitation_mm=1.0, precipitation_probability=60)
        for hour in range(1, 6)
    ]
    assert rain_soon(rows, now)["total_mm"] == 2.0


def test_best_outdoor_window_skips_rainy_hours():
    start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)  # 05:30 IST
    rows = [
        WeatherRecord(
            valid_time=start + timedelta(hours=hour),
            temperature_c=28,
            relative_humidity=60,
            precipitation_mm=5 if hour == 1 else 0,
            precipitation_probability=90 if hour == 1 else 10,
        )
        for hour in range(6)
    ]
    window = best_outdoor_window(rows)
    assert window["start"] == rows[2].valid_time
    assert window["end"] == rows[4].valid_time + timedelta(hours=1)


def test_week_plan_rates_days(api_client, area):
    forecast(area, [{"temperature_c": 30, "relative_humidity": 60, "precipitation_mm": 2, "weather_code": 61}] * 30)

    body = api_client.get("/api/v1/planner/week/", {"area": area.slug}).json()

    assert body["days"]
    assert {day["rating"] for day in body["days"]} <= {"good", "fair", "poor"}


def test_routes_are_private_and_limited(auth_client, api_client, user):
    created = auth_client.post(
        "/api/v1/users/me/routes/", {"label": "College", "points": ROUTE_POINTS}, format="json"
    )
    assert created.status_code == 201

    other = get_user_model().objects.create_user(
        username="b", email="b@example.com", password="a-very-long-password-123"
    )
    route = SavedRoute.objects.create(user=other, label="Theirs", points=ROUTE_POINTS)
    assert auth_client.get(f"/api/v1/users/me/routes/{route.id}/status/").status_code == 404
    assert auth_client.delete(f"/api/v1/users/me/routes/{route.id}/").status_code == 404
    assert api_client.get("/api/v1/users/me/routes/").status_code in {401, 403}

    for index in range(4):
        SavedRoute.objects.create(user=user, label=f"Route {index}", points=ROUTE_POINTS)
    extra = auth_client.post(
        "/api/v1/users/me/routes/", {"label": "One more", "points": ROUTE_POINTS}, format="json"
    )
    assert extra.status_code == 400


@pytest.mark.parametrize("points", [[[22.5, 88.3]], [["a", "b"], [22.5, 88.3]], [[95, 88], [22.5, 88.3]]])
def test_invalid_route_points_are_rejected(auth_client, points):
    response = auth_client.post("/api/v1/users/me/routes/", {"label": "Bad", "points": points}, format="json")
    assert response.status_code == 400


def test_route_status_finds_reports_on_the_corridor(auth_client, area, user):
    near = report(area, water_depth="waist")
    report(area, latitude=22.56, longitude=88.375)
    route = SavedRoute.objects.create(user=user, label="College", points=ROUTE_POINTS)

    body = auth_client.get(f"/api/v1/users/me/routes/{route.id}/status/").json()

    assert body["summary"] == "serious_reports"
    assert [item["id"] for item in body["reports"]] == [str(near.id)]


def test_clear_route_never_says_safe(auth_client, area, user):
    route = SavedRoute.objects.create(user=user, label="College", points=ROUTE_POINTS)
    body = auth_client.get(f"/api/v1/users/me/routes/{route.id}/status/").json()
    assert body["summary"] == "no_reports"
    assert "does not mean the road is clear" in body["note"]


def test_alerts_reach_route_owner_once_and_skip_own_reports(area, user):
    SavedRoute.objects.create(user=user, label="College", points=ROUTE_POINTS)
    SavedLocation.objects.create(user=user, label="Home", latitude=22.555, longitude=88.3505)
    report(area, reporter=user, latitude=22.5555)
    report(area, reporter=other_user())

    evaluate_alerts()
    evaluate_alerts()

    notifications = Notification.objects.filter(user=user)
    assert notifications.count() == 1
    assert "on College" in notifications.get().title


@pytest.mark.parametrize("expires_in", [timedelta(hours=4), None])
def test_official_alert_notifies_users_with_alerts_on(area, user, expires_in):
    muted = other_user()
    UserPreference.objects.create(user=muted, alerts_enabled=False)
    now = timezone.now()
    OfficialAlert.objects.create(
        source=DataSource.objects.get(slug="sachet"),
        external_id="alert",
        title="Heavy rain warning",
        issued_at=now,
        retrieved_at=now,
        expires_at=now + expires_in if expires_in else None,
        areas_text="Kolkata",
    )

    evaluate_alerts()

    assert Notification.objects.filter(user=user, kind="official_alert").count() == 1
    assert not Notification.objects.filter(user=muted).exists()


def test_notifications_list_and_mark_read(auth_client, api_client, user):
    Notification.objects.create(user=user, kind="heat", title="Hot", dedupe_key="a")

    assert api_client.get("/api/v1/notifications/").status_code in {401, 403}
    assert auth_client.get("/api/v1/notifications/").json()["unread"] == 1
    auth_client.post("/api/v1/notifications/read/")
    assert auth_client.get("/api/v1/notifications/").json()["unread"] == 0


def test_telegram_needs_a_token_and_keeps_it_out_of_logs(settings, user, caplog):
    preference, _ = UserPreference.objects.get_or_create(user=user)
    preference.telegram_chat_id = "12345"
    preference.quiet_hours = False
    notification = Notification.objects.create(user=user, kind="heat", title="Hot", dedupe_key="a")

    settings.TELEGRAM_BOT_TOKEN = ""
    assert deliver_telegram(notification, preference) is False

    settings.TELEGRAM_BOT_TOKEN = "secret-bot-token"
    error = requests.ConnectionError("https://api.telegram.org/botsecret-bot-token/sendMessage failed")
    with mock.patch("apps.notifications.services.requests.post", side_effect=error):
        assert deliver_telegram(notification, preference) is False
    assert "secret-bot-token" not in caplog.text


def test_impact_counts_contributions(auth_client, area, user):
    report(area, reporter=user)

    body = auth_client.get("/api/v1/users/me/impact/").json()

    assert body["reports"] == 1
    assert body["level"] == "reporter"


def test_gps_accuracy_is_stored_but_not_public(auth_client, area, api_client):
    created = auth_client.post(
        "/api/v1/incidents/",
        {
            "area": area.slug,
            "category": "transport_disruption",
            "occurred_at": timezone.now().isoformat(),
            "latitude": 22.553,
            "longitude": 88.352,
            "location_accuracy_m": 18.5,
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    assert "location_accuracy_m" not in created.json()
    assert "location_accuracy_m" not in api_client.get("/api/v1/incidents/live/").content.decode()
