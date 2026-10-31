from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.core.geometry import point_geojson
from apps.core.models import DataSource
from apps.environment.models import EnvironmentalObservation, SatelliteScene
from apps.heat.models import ModelVersion
from apps.incidents.models import IncidentCategory, IncidentReport, IncidentStatus
from apps.intelligence.models import Recommendation
from apps.locations.models import GridCell
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


@pytest.mark.django_db
def test_weather_current_forecast_and_history_states(api_client, weather_location):
    now = timezone.now()
    make_weather(
        weather_location,
        kind=WeatherKind.CURRENT,
        valid_time=now,
        temperature_c=33.2,
        apparent_temperature_c=39.0,
        relative_humidity=70,
        weather_code=2,
    )
    make_weather(
        weather_location,
        kind=WeatherKind.HOURLY,
        valid_time=now + timedelta(hours=2),
        precipitation_mm=4.5,
        precipitation_probability=80,
        temperature_c=31.0,
    )
    make_weather(
        weather_location,
        kind=WeatherKind.DAILY,
        valid_time=now - timedelta(days=3),
        temperature_max_c=35.0,
        temperature_min_c=27.0,
        precipitation_mm=12.0,
    )

    current = api_client.get("/api/v1/weather/current/").json()
    assert current["state"] == "AVAILABLE"
    assert current["record"]["temperature_c"] == 33.2
    assert current["record"]["condition"]["label"]
    assert current["source"]["slug"] == "open_meteo"

    forecast = api_client.get("/api/v1/weather/forecast/").json()
    assert forecast["state"] == "AVAILABLE"
    assert len(forecast["hourly"]) == 1
    assert forecast["hourly"][0]["precipitation_probability"] == 80

    history = api_client.get("/api/v1/weather/history/").json()
    assert history["state"] == "AVAILABLE"
    assert len(history["daily"]) == 1


@pytest.mark.django_db
def test_weather_endpoints_are_unavailable_without_data(api_client, area):
    response = api_client.get("/api/v1/weather/current/")
    assert response.status_code == 200
    assert response.json()["state"] == "UNAVAILABLE"
    assert response.json()["record"] is None


@pytest.mark.django_db
def test_rainfall_forecast_derives_from_weather_records(api_client, weather_location):
    now = timezone.now()
    make_weather(
        weather_location,
        kind=WeatherKind.HOURLY,
        valid_time=now + timedelta(hours=1),
        precipitation_mm=2.0,
        precipitation_probability=60,
    )
    make_weather(
        weather_location,
        kind=WeatherKind.HOURLY,
        valid_time=now + timedelta(hours=2),
        precipitation_mm=5.0,
        precipitation_probability=90,
    )
    response = api_client.get("/api/v1/rainfall/forecast/").json()
    assert response["state"] == "AVAILABLE"
    assert response["summary"]["next_24h_total_mm"] == 7.0
    assert response["summary"]["next_24h_max_probability_pct"] == 90
    assert response["summary"]["peak_hour_mm"] == 5.0


@pytest.mark.django_db
def test_alerts_air_quality_environment_and_heat_report_unavailable(api_client, area):
    alerts = api_client.get("/api/v1/alerts/").json()
    assert alerts["state"] == "UNAVAILABLE"
    assert "official alert feed" in alerts["reason"]

    air = api_client.get("/api/v1/air-quality/stations/").json()
    assert air["state"] == "UNAVAILABLE"
    assert "CPCB" in air["reason"]

    layers = api_client.get("/api/v1/environment/layers/").json()
    assert layers["state"] == "UNAVAILABLE"
    assert layers["reason"]

    heat = api_client.get("/api/v1/heat/predictions/").json()
    assert heat["state"] == "UNAVAILABLE"
    assert heat["results"] == []
    assert "not measured air temperature" in heat["disclaimer"]

    model_info = api_client.get("/api/v1/heat/model-info/").json()
    assert model_info["state"] == "UNAVAILABLE"
    assert model_info["active_model"] is None


@pytest.mark.django_db
def test_heat_model_metrics_are_only_what_was_registered(api_client, db):
    ModelVersion.objects.create(
        name="lst-baseline",
        version="0.1.0",
        task="lst_estimation",
        algorithm="xgboost",
        target="predicted_lst_c",
        dataset_version="fixture-not-operational",
        feature_schema={"features": ["ndvi"]},
        metrics={"mae_c": 2.1, "rmse_c": 3.0, "r2": 0.71, "n_test": 40},
        is_active=True,
        is_operational=False,
        limitations="Trained on a small development subset; not operational.",
    )
    response = api_client.get("/api/v1/heat/model-info/").json()
    assert response["state"] == "AVAILABLE"
    assert response["active_model"]["metrics"]["mae_c"] == 2.1
    assert response["active_model"]["is_operational"] is False


@pytest.mark.django_db
def test_heat_hotspots_use_observed_lst(api_client, grid):
    source = DataSource.objects.get(slug="landsat")
    scene = SatelliteScene.objects.create(
        source=source,
        scene_id="LC09-TEST",
        platform="Landsat 9",
        collection="C2L2",
        acquired_at=timezone.now(),
        processing_level="L2SP",
    )
    cells = list(GridCell.objects.filter(area=grid)[:10])
    for index, cell in enumerate(cells):
        EnvironmentalObservation.objects.create(
            scene=scene,
            cell=cell,
            observed_on=timezone.now().date(),
            lst_c=35.0 + index,
            valid_pixel_fraction=0.9,
            processing_version="test-1",
        )
    response = api_client.get("/api/v1/heat/hotspots/").json()
    assert response["state"] == "AVAILABLE"
    assert response["count"] >= 1
    assert response["threshold_c"] is not None
    assert "not an ML prediction" in response["method"]


@pytest.mark.django_db
def test_insights_without_data_are_caveated_not_fabricated(api_client, area):
    response = api_client.get("/api/v1/insights/")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "PARTIAL"
    rule_ids = {item["rule_id"] for item in body["insights"]}
    assert rule_ids == {"data_availability_caveat"}
    caveat = body["insights"][0]
    assert caveat["kind"] == "data_availability"
    assert len(caveat["evidence"]) >= 2
    assert all(item["source"] for item in caveat["evidence"])


@pytest.mark.django_db
def test_heat_insight_includes_source_and_timestamp(api_client, weather_location):
    now = timezone.now()
    make_weather(
        weather_location,
        kind=WeatherKind.CURRENT,
        valid_time=now,
        temperature_c=35.0,
        apparent_temperature_c=41.5,
    )
    body = api_client.get("/api/v1/insights/").json()
    heat = next(item for item in body["insights"] if item["rule_id"] == "heat_stress")
    assert heat["severity"] == "warning"
    assert heat["evidence"][0]["source"]["slug"] == "open_meteo"
    assert heat["evidence"][0]["observed_at"] is not None
    assert heat["evidence"][0]["evidence_type"] == "observation"
    assert any("not official" in caveat.lower() for caveat in heat["caveats"])


@pytest.mark.django_db
def test_verified_incident_creates_community_insight(api_client, area, user):
    now = timezone.now()
    source = DataSource.objects.get(slug="community_reports")
    IncidentReport.objects.create(
        reporter=user,
        area=area,
        category=IncidentCategory.WATERLOGGING,
        description="Water above the kerb near the market.",
        occurred_at=now - timedelta(hours=1),
        point=point_geojson(22.553, 88.352),
        latitude=22.553,
        longitude=88.352,
        status=IncidentStatus.VERIFIED,
        verified_at=now - timedelta(minutes=30),
        source=source,
    )
    body = api_client.get("/api/v1/insights/").json()
    insight = next(item for item in body["insights"] if item["rule_id"] == "verified_waterlogging")
    assert insight["evidence"][0]["evidence_type"] == "community_report"
    assert insight["evidence"][0]["source"]["slug"] == "community_reports"
    assert any("not a flood forecast" in caveat for caveat in insight["caveats"])


@pytest.mark.django_db
def test_only_moderators_can_persist_insights(moderator_client, auth_client, area):
    assert auth_client.post("/api/v1/insights/generate/", {}, format="json").status_code == 403
    response = moderator_client.post("/api/v1/insights/generate/", {"area": "kolkata"}, format="json")
    assert response.status_code == 200
    assert response.json()["persisted"] == 1
    assert Recommendation.objects.count() == 1

    history = moderator_client.get("/api/v1/insights/history/").json()
    assert history["state"] == "AVAILABLE"
    assert history["count"] == 1
    assert history["results"][0]["evidence"]


@pytest.mark.django_db
def test_unknown_area_returns_structured_error(api_client):
    response = api_client.get("/api/v1/insights/", {"area": "atlantis"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
