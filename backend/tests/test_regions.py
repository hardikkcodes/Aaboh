"""Multiple areas, state-level alert matching and forecast agreement."""

from __future__ import annotations

from datetime import date, timedelta
from unittest import mock

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.alerts.models import OfficialAlert
from apps.alerts.services import alert_match
from apps.core.geometry import point_geojson
from apps.core.models import DataSource, IngestionRun, IngestionRunStatus
from apps.incidents.services import create_incident, live_reports
from apps.intelligence.place_status import build_place_status
from apps.intelligence.today import model_agreement
from apps.locations.models import Area, AreaLevel
from apps.locations.services.regions import area_for_point
from apps.weather.models import DailyModelForecast, WeatherLocation
from apps.weather.services import ingest_model_comparison

pytestmark = pytest.mark.django_db


@pytest.fixture
def regions(area):
    osm, _ = DataSource.objects.get_or_create(slug="osm", defaults={"name": "OSM", "provider_type": "community"})
    Area.objects.filter(pk=area.pk).update(source=osm)
    call_command("bootstrap_regions", verbosity=0)
    return area


def alert(text: str, severity="severe") -> OfficialAlert:
    now = timezone.now()
    return OfficialAlert.objects.create(
        source=DataSource.objects.get(slug="sachet"),
        external_id=text,
        title="Warning",
        severity=severity,
        issued_at=now,
        retrieved_at=now,
        expires_at=now + timedelta(hours=6),
        areas_text=text,
    )


def test_bootstrap_adds_zones_and_districts(regions):
    north = Area.objects.get(slug="north-kolkata")
    district = Area.objects.get(slug="south-24-parganas")

    assert north.level == AreaLevel.ZONE and north.data_area == regions
    assert district.neighbourhoods.count() > 100
    assert district.focus == (22.3589, 88.4315)


def test_points_resolve_to_the_right_area(regions):
    assert area_for_point(22.56, 88.36).slug == "kolkata"
    assert area_for_point(22.7229, 88.4810).slug == "north-24-parganas"
    assert area_for_point(22.2, 88.45).slug == "south-24-parganas"
    assert area_for_point(25.0, 85.0) is None


def test_reports_belong_to_the_area_they_fall_in(auth_client, regions):
    response = auth_client.post(
        "/api/v1/incidents/",
        {"category": "waterlogging", "occurred_at": timezone.now().isoformat(), "latitude": 22.7229, "longitude": 88.481},
        format="json",
    )
    assert response.status_code == 201, response.content
    assert response.json()["area"]["slug"] == "north-24-parganas"


def test_reports_outside_coverage_are_rejected(auth_client, regions):
    response = auth_client.post(
        "/api/v1/incidents/",
        {"category": "waterlogging", "occurred_at": timezone.now().isoformat(), "latitude": 25.0, "longitude": 85.0},
        format="json",
    )
    assert response.status_code == 400


def test_zones_show_only_their_own_reports(regions):
    report = create_incident(
        reporter=None,
        area=regions,
        category="waterlogging",
        occurred_at=timezone.now() - timedelta(minutes=5),
        latitude=22.57,
        longitude=88.36,
    )
    assert [item.id for item in live_reports(Area.objects.get(slug="north-kolkata"))] == [report.id]
    assert live_reports(Area.objects.get(slug="south-kolkata")) == []
    assert [item.id for item in live_reports(regions)] == [report.id]


@pytest.mark.parametrize(
    ("text", "slug", "expected"),
    [
        ("Kolkata, West Bengal", "kolkata", "named"),
        ("Kolkata, West Bengal", "south-24-parganas", "state"),
        ("South 24 Parganas, West Bengal", "south-24-parganas", "named"),
        ("South 24 Parganas, West Bengal", "north-24-parganas", "state"),
        ("9 districts of West Bengal", "north-24-parganas", "state"),
        ("4 districts of Uttarakhand", "kolkata", None),
    ],
)
def test_alert_matching(regions, text, slug, expected):
    assert alert_match(alert(text), Area.objects.get(slug=slug)) == expected


def test_zone_inherits_city_alerts(regions):
    assert alert_match(alert("Kolkata"), Area.objects.get(slug="south-kolkata")) == "named"


def test_state_alert_is_shown_but_softer_than_a_named_one(api_client, regions):
    alert("9 districts of West Bengal", severity="extreme")
    IngestionRun.objects.create(
        source=DataSource.objects.get(slug="sachet"), status=IngestionRunStatus.SUCCESS, finished_at=timezone.now()
    )

    status = build_place_status(regions)["status"]
    body = api_client.get("/api/v1/alerts/", {"area": "kolkata"}).json()

    assert status["level"] == "watch"
    assert body["count"] == 1 and body["named_count"] == 0
    assert body["results"][0]["match"] == "state"
    assert "may include" in body["feed_message"]


def test_named_alert_is_listed_before_state_alert(api_client, regions):
    alert("West Bengal")
    alert("Kolkata")
    assert [item["match"] for item in api_client.get("/api/v1/alerts/").json()["results"]] == ["named", "state"]


def test_unknown_area_is_rejected(api_client, regions):
    assert api_client.get("/api/v1/alerts/", {"area": "nowhere"}).status_code == 400


def location(area) -> WeatherLocation:
    return WeatherLocation.objects.create(
        area=area,
        name="Point",
        point=point_geojson(22.56, 88.36),
        latitude=22.56,
        longitude=88.36,
        source=DataSource.objects.get(slug="open_meteo"),
        provider_location_key="test",
    )


@pytest.mark.parametrize(
    ("rain", "level"),
    [([0, 0.5, 1], "high"), ([12, 20, 30], "high"), ([0, 0, 5], "medium"), ([0, 1, 40], "low"), ([0, 30, 40], "low")],
)
def test_model_agreement(area, rain, level):
    place = location(area)
    day = date(2026, 11, 1)
    for index, value in enumerate(rain):
        DailyModelForecast.objects.create(
            location=place, model=f"m{index}", valid_date=day, rain_mm=value, retrieved_at=timezone.now()
        )
    assert model_agreement(area, day)["level"] == level


def test_agreement_is_unknown_without_enough_models(area):
    assert model_agreement(area, date(2026, 11, 1)) is None


def test_model_comparison_is_stored_per_model(area):
    payload = {
        "daily": {
            "time": ["2026-11-01"],
            "precipitation_sum_ecmwf_ifs025": [1.0],
            "temperature_2m_max_ecmwf_ifs025": [30.0],
            "precipitation_sum_gfs_seamless": [2.0],
            "temperature_2m_max_gfs_seamless": [31.0],
            "precipitation_sum_icon_seamless": [None],
            "temperature_2m_max_icon_seamless": [None],
        }
    }
    with mock.patch("apps.weather.services.open_meteo.fetch_model_comparison", return_value=payload):
        ingest_model_comparison(location(area))
    assert DailyModelForecast.objects.filter(rain_mm__isnull=False).count() == 2
