from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.core.geometry import point_geojson
from apps.core.models import DataSource
from apps.incidents.models import IncidentCategory, IncidentReport, IncidentStatus
from apps.weather.models import WeatherKind, WeatherLocation, WeatherRecord


@pytest.fixture
def weather_location(area):
    source = DataSource.objects.get(slug="open_meteo")
    return WeatherLocation.objects.create(
        area=area,
        name="Kolkata (forecast point)",
        point=point_geojson(22.56, 88.36),
        latitude=22.56,
        longitude=88.36,
        source=source,
        provider_location_key="22.5600,88.3600",
    )


def make_weather(location, *, kind, valid_time, **values):
    return WeatherRecord.objects.create(
        location=location,
        source=location.source,
        kind=kind,
        valid_time=valid_time,
        retrieved_at=timezone.now(),
        **values,
    )


def make_report(area, neighbourhood, *, status=IncidentStatus.SUBMITTED, category=IncidentCategory.WATERLOGGING):
    return IncidentReport.objects.create(
        area=area,
        neighbourhood=neighbourhood,
        category=category,
        description="Water is standing across the road near the crossing.",
        occurred_at=timezone.now() - timedelta(minutes=30),
        point=point_geojson(neighbourhood.latitude, neighbourhood.longitude),
        latitude=neighbourhood.latitude,
        longitude=neighbourhood.longitude,
        status=status,
        is_public=True,
        source=DataSource.objects.get(slug="community_reports"),
    )


@pytest.mark.django_db
def test_place_status_is_honest_when_everything_is_unavailable(api_client, area):
    response = api_client.get("/api/v1/place-status/")
    assert response.status_code == 200
    payload = response.json()

    assert payload["place"]["label"] == "Kolkata"
    assert payload["place"]["resolution"] == "area"
    assert payload["status"]["level"] == "unknown"
    assert payload["waterlogging"]["level"] == "unknown"
    assert payload["waterlogging"]["method"]["is_ml"] is False
    assert any("not a trained" in caveat for caveat in payload["waterlogging"]["caveats"])
    assert "alert feed is unavailable" in payload["alerts"]["reason"]
    assert "CPCB" in payload["air_quality"]["reason"]
    assert payload["reports"]["total"] == 0
    assert payload["coverage"]["available"] == 0


@pytest.mark.django_db
def test_place_status_rule_based_waterlogging_uses_rain_and_reports(
    api_client, area, neighbourhood, weather_location
):
    now = timezone.now()
    make_weather(
        weather_location,
        kind=WeatherKind.HOURLY,
        valid_time=now + timedelta(hours=1),
        precipitation_mm=12.0,
        precipitation_probability=85,
    )
    make_weather(
        weather_location,
        kind=WeatherKind.HOURLY,
        valid_time=now + timedelta(hours=2),
        precipitation_mm=18.0,
        precipitation_probability=95,
    )
    make_report(area, neighbourhood, status=IncidentStatus.VERIFIED)

    payload = api_client.get(
        "/api/v1/place-status/",
        {"area": area.slug, "neighbourhood": neighbourhood.slug},
    ).json()

    assert payload["place"]["label"] == "Park Street, Kolkata"
    assert payload["place"]["resolution"] == "neighbourhood"
    assert payload["rain"]["next_24h_total_mm"] == 30.0
    assert payload["waterlogging"]["level"] == "elevated"
    assert payload["waterlogging"]["points"] == 3
    assert payload["waterlogging"]["reports"]["verified"] == 1
    assert payload["reports"]["verified"] == 1
    assert payload["status"]["level"] == "watch"
    assert any("waterlogging" in reason.lower() for reason in payload["status"]["reasons"])


@pytest.mark.django_db
def test_place_status_unverified_reports_add_at_most_one_point(
    api_client, area, neighbourhood
):
    make_report(area, neighbourhood, status=IncidentStatus.SUBMITTED)
    make_report(area, neighbourhood, status=IncidentStatus.SUBMITTED)

    payload = api_client.get(
        f"/api/v1/areas/{area.slug}/place-status/",
        {"neighbourhood": neighbourhood.slug},
    ).json()

    assert payload["waterlogging"]["reports"]["unverified"] == 2
    assert payload["waterlogging"]["points"] == 1
    assert payload["waterlogging"]["level"] == "reports_only"
    assert payload["waterlogging"]["state"] == "PARTIAL"


@pytest.mark.django_db
def test_place_status_recent_rain_covers_yesterday_and_today(api_client, area, weather_location):
    now = timezone.now()
    make_weather(
        weather_location,
        kind=WeatherKind.DAILY,
        valid_time=now - timedelta(days=1),
        precipitation_mm=12.0,
    )
    make_weather(
        weather_location,
        kind=WeatherKind.DAILY,
        valid_time=now,
        precipitation_mm=4.0,
    )

    payload = api_client.get("/api/v1/place-status/").json()

    assert payload["recent_rain"]["days_covered"] == 2
    assert payload["recent_rain"]["max_daily_mm"] == 12.0
    assert payload["recent_rain"]["total_mm"] == 16.0


@pytest.mark.django_db
def test_place_status_rejects_unknown_neighbourhood(api_client, area):
    response = api_client.get(
        f"/api/v1/areas/{area.slug}/place-status/",
        {"neighbourhood": "does-not-exist"},
    )
    assert response.status_code == 400
    assert "neighbourhood" in response.json()["error"]["details"]
