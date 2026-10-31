from __future__ import annotations

import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse

from apps.core.models import DataSource, IngestionRun, IngestionRunStatus
from apps.core.quality import DataState, freshness_state, source_availability
from apps.locations.models import GridCell
from apps.locations.services.grid import generate_grid


@pytest.mark.django_db
def test_api_root_lists_public_endpoints(api_client):
    response = api_client.get("/api/v1/")
    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["endpoints"]["weather_forecast"].endswith("/api/v1/weather/forecast/")
    assert body["documentation"]["openapi"].endswith("/api/schema/")


@pytest.mark.django_db
def test_health_and_readiness(api_client, area):
    health = api_client.get(reverse("core:health"))
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = api_client.get(reverse("core:readiness"))
    assert ready.status_code == 200
    assert ready.json() == {"ready": True, "reason": None}


@pytest.mark.django_db
def test_readiness_reports_missing_geography(api_client):
    response = api_client.get(reverse("core:readiness"))
    assert response.status_code == 503
    assert response.json()["reason"] == "geography_not_bootstrapped"


@pytest.mark.django_db
def test_data_status_is_honest_about_missing_credentials(api_client):
    response = api_client.get(reverse("core:data-status"))
    assert response.status_code == 200
    modules = response.json()["modules"]
    assert modules["alerts"]["state"] == DataState.UNAVAILABLE
    assert "IMD_API_KEY" in modules["alerts"]["reason"]
    assert modules["air_quality"]["state"] == DataState.UNAVAILABLE
    assert modules["environment"]["state"] == DataState.UNAVAILABLE
    assert modules["community"]["state"] == DataState.UNAVAILABLE


@pytest.mark.django_db
def test_source_availability_marks_stale_and_failed_states():
    source = DataSource.objects.create(
        slug="test-source",
        name="Test source",
        provider_type="supplementary",
        expected_refresh_minutes=60,
    )
    assert source_availability(source)["state"] == DataState.UNAVAILABLE

    IngestionRun.objects.create(
        source=source,
        status=IngestionRunStatus.FAILED,
        error_message="provider timed out",
    )
    availability = source_availability(source)
    assert availability["state"] == DataState.UNAVAILABLE
    assert availability["last_error"] == "provider timed out"

    IngestionRun.objects.create(source=source, status=IngestionRunStatus.SUCCESS)
    assert source_availability(source)["state"] == DataState.AVAILABLE


def test_freshness_state_boundaries():
    from datetime import timedelta

    from django.utils import timezone

    now = timezone.now()
    assert freshness_state(None) == DataState.UNAVAILABLE
    assert freshness_state(now - timedelta(minutes=5), max_age=timedelta(hours=1), now=now) == DataState.AVAILABLE
    assert freshness_state(now - timedelta(hours=2), max_age=timedelta(hours=1), now=now) == DataState.STALE
    assert freshness_state(now + timedelta(hours=2), now=now) == DataState.INVALID


@pytest.mark.django_db
def test_grid_generation_is_deterministic(grid):
    first = list(GridCell.objects.order_by("row", "col").values_list("code", "row", "col"))
    assert first
    generate_grid(grid, version="TEST-1KM-V1")
    second = list(GridCell.objects.order_by("row", "col").values_list("code", "row", "col"))
    assert first == second
    cell = GridCell.objects.first()
    assert cell.definition.crs == "EPSG:32645"
    assert 0 < cell.coverage_fraction <= 1
    assert cell.area_km2 > 0
    assert cell.centroid["type"] == "Point"


@pytest.mark.django_db
def test_area_detail_and_grid_cells(api_client, grid):
    detail = api_client.get(reverse("locations:area-detail", args=[grid.slug]))
    assert detail.status_code == 200
    body = detail.json()
    assert body["grid_versions"][0]["cell_size_m"] == 1000

    cells = api_client.get(reverse("locations:area-grid-cells", args=[grid.slug]))
    assert cells.status_code == 200
    payload = cells.json()
    assert payload["crs"] == "EPSG:32645"
    assert payload["count"] == len(payload["cells"])
    assert payload["cells"][0]["geometry"]["type"] in {"Polygon", "MultiPolygon"}


@pytest.mark.django_db
def test_export_grid_geojson_for_earth_engine(grid, tmp_path):
    output = tmp_path / "kolkata-grid.geojson"
    call_command(
        "export_grid_geojson",
        area=grid.slug,
        grid_version="TEST-1KM-V1",
        output=str(output),
    )

    collection = json.loads(output.read_text(encoding="utf-8"))
    assert collection["type"] == "FeatureCollection"
    assert collection["metadata"]["crs"] == "EPSG:4326"
    assert collection["metadata"]["cell_count"] == GridCell.objects.count()
    first = collection["features"][0]
    assert first["type"] == "Feature"
    assert first["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert first["properties"]["cell_code"]
    assert first["properties"]["centroid_lat"]


@pytest.mark.django_db
def test_export_grid_geojson_refuses_to_overwrite(grid, tmp_path):
    output = tmp_path / "kolkata-grid.geojson"
    output.write_text("{}", encoding="utf-8")
    with pytest.raises(CommandError, match="already exists"):
        call_command(
            "export_grid_geojson",
            area=grid.slug,
            grid_version="TEST-1KM-V1",
            output=str(output),
        )


@pytest.mark.django_db
def test_location_search_matches_neighbourhood(api_client, neighbourhood):
    response = api_client.get(reverse("locations:location-search"), {"q": "park"})
    assert response.status_code == 200
    results = response.json()["results"]
    assert any(item["name"] == "Park Street" for item in results)
