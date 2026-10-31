"""Features built only from stored records. With no records they must stay empty."""

from __future__ import annotations

from datetime import timedelta
from unittest import mock

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.air_quality.models import AirForecastHour
from apps.air_quality.services import ingest_air_forecast
from apps.core.models import DataSource
from apps.incidents.models import CommunitySpot
from apps.incidents.services import create_incident
from apps.intelligence.today import build_today, cleanest_air_window

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_rate_limits():
    cache.clear()
    yield
    cache.clear()


def report(area, days_ago=0, **extra):
    return create_incident(
        reporter=None,
        area=area,
        category=extra.pop("category", "waterlogging"),
        occurred_at=timezone.now() - timedelta(days=days_ago, minutes=10),
        latitude=22.553,
        longitude=88.352,
        **extra,
    )


def test_nothing_is_preloaded(api_client, area):
    assert api_client.get("/api/v1/spots/").json() == []
    assert api_client.get("/api/v1/incidents/live/").json()["count"] == 0
    stats = api_client.get("/api/v1/incidents/stats/").json()
    assert stats["total"] == 0
    assert stats["recurring_water_spots"] == []
    assert api_client.get("/api/v1/incidents/export/").content.decode().count("\n") == 1


def test_recurring_spot_needs_two_separate_days(api_client, area, neighbourhood):
    report(area)
    report(area)
    assert api_client.get("/api/v1/incidents/stats/").json()["recurring_water_spots"] == []

    report(area, days_ago=3)
    spots = api_client.get("/api/v1/incidents/stats/").json()["recurring_water_spots"]
    assert spots == [{"name": neighbourhood.name, "slug": neighbourhood.slug, "reports": 3, "days": 2}]


def test_export_has_no_text_or_exact_location(api_client, area, neighbourhood):
    report(area, description="My neighbour Ravi's house is flooded")
    body = api_client.get("/api/v1/incidents/export/").content.decode()
    assert "Ravi" not in body
    assert "22.553," in body
    assert "occurred_hour" in body


def test_spots_need_sign_in_and_stay_in_the_area(api_client, auth_client, area):
    payload = {"kind": "drinking_water", "name": "Public tap by the park", "latitude": 22.55, "longitude": 88.35}
    assert api_client.post("/api/v1/spots/", payload, format="json").status_code in {401, 403}
    assert auth_client.post("/api/v1/spots/", payload, format="json").status_code == 201
    outside = {**payload, "latitude": 23.5}
    assert auth_client.post("/api/v1/spots/", outside, format="json").status_code == 400


def test_only_the_owner_or_moderator_removes_a_spot(auth_client, moderator_client, api_client, area, user):
    spot = CommunitySpot.objects.create(area=area, kind="shelter", name="Hall", latitude=22.55, longitude=88.35)
    assert auth_client.delete(f"/api/v1/spots/{spot.id}/").status_code == 403
    assert moderator_client.delete(f"/api/v1/spots/{spot.id}/").status_code == 204


def test_air_window_uses_the_cleanest_daytime_hours(area):
    source = DataSource.objects.get(slug="cams_air")
    start = (timezone.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)  # 05:30 IST
    for hour, pm25 in enumerate([80, 20, 25, 90, 90]):
        AirForecastHour.objects.create(
            area=area, source=source, valid_time=start + timedelta(hours=hour), retrieved_at=timezone.now(), pm25=pm25
        )

    window = cleanest_air_window(area, start - timedelta(hours=2))

    assert window["start"] == start + timedelta(hours=1)
    assert window["pm25"] == 25


def test_missing_air_forecast_is_not_invented(area):
    assert build_today(area)["cleanest_air_window"] is None


def test_air_forecast_ingestion_records_failure_without_faking(area):
    with mock.patch(
        "apps.air_quality.services.open_meteo.fetch_air_forecast", side_effect=RuntimeError("down")
    ), pytest.raises(Exception, match="down"):
        ingest_air_forecast(area)
    assert not AirForecastHour.objects.exists()


def test_model_status_reports_live_progress(api_client, area):
    report(area)
    body = api_client.get("/api/v1/system/models/").json()
    waterlogging = body["waiting"][0]
    assert waterlogging["progress"][0]["value"] == 1
    assert waterlogging["progress"][0]["target"] == 300


def test_timeline_is_empty_without_a_forecast(area):
    assert build_today(area)["timeline"] == []
