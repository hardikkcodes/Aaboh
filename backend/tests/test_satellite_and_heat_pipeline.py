from __future__ import annotations

import csv
import json
from datetime import UTC, datetime

import pytest

from apps.environment.models import EnvironmentalObservation, SatelliteScene
from apps.heat.models import CellPrediction, ModelVersion, PredictionRun, PredictionRunStatus
from apps.heat.services import HeatModelError, ingest_predictions, register_artifact
from apps.locations.models import GridCell

pytestmark = pytest.mark.django_db


def _write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


ENV_FIELDS = [
    "cell_code",
    "observed_on",
    "acquired_at",
    "scene_id",
    "lst_c",
    "ndvi",
    "ndbi",
    "mndwi",
    "valid_pixel_fraction",
    "cloud_cover_pct",
]


def test_landsat_ingestion_preserves_scene_provenance(grid, tmp_path):
    from apps.environment.services import ingest_landsat_observations

    cells = list(GridCell.objects.filter(definition__area=grid)[:3])
    rows = []
    for cell in cells:
        rows.append(
            {
                "cell_code": cell.code,
                "observed_on": "2025-04-10",
                "acquired_at": "2025-04-10T05:22:11Z",
                "scene_id": "LC09_TEST_001",
                "lst_c": "38.5",
                "ndvi": "0.21",
                "ndbi": "0.32",
                "mndwi": "-0.18",
                "valid_pixel_fraction": "0.82",
                "cloud_cover_pct": "6.5",
            }
        )
    dataset = _write_csv(tmp_path / "observations.csv", rows, ENV_FIELDS)

    result = ingest_landsat_observations(grid, dataset, grid_version="TEST-1KM-V1")
    assert result["written"] == 3
    assert result["scenes"] == 1
    scene = SatelliteScene.objects.get(scene_id="LC09_TEST_001")
    assert scene.acquired_at == datetime(2025, 4, 10, 5, 22, 11, tzinfo=UTC)
    observation = EnvironmentalObservation.objects.first()
    assert observation.lst_c == 38.5
    assert observation.processing_version == "landsat-c2l2-v1"


def test_landsat_ingestion_marks_unknown_acquisition_time(grid, tmp_path):
    from apps.environment.services import ingest_landsat_observations

    cell = GridCell.objects.filter(definition__area=grid).first()
    dataset = _write_csv(
        tmp_path / "no-time.csv",
        [
            {
                "cell_code": cell.code,
                "observed_on": "2025-04-10",
                "acquired_at": "",
                "scene_id": "LC09_TEST_002",
                "lst_c": "35",
                "ndvi": "0.3",
                "ndbi": "0.2",
                "mndwi": "-0.1",
                "valid_pixel_fraction": "0.7",
                "cloud_cover_pct": "10",
            }
        ],
        ENV_FIELDS,
    )
    ingest_landsat_observations(grid, dataset, grid_version="TEST-1KM-V1")
    scene = SatelliteScene.objects.get(scene_id="LC09_TEST_002")
    assert scene.metadata["acquisition_time_unknown"] is True


def test_landsat_ingestion_rejects_unknown_cells(grid, tmp_path):
    from apps.environment.services import SatelliteIngestionError, ingest_landsat_observations

    dataset = _write_csv(
        tmp_path / "wrong-cells.csv",
        [
            {
                "cell_code": "NOT-A-CELL",
                "observed_on": "2025-04-10",
                "acquired_at": "2025-04-10T05:22:11Z",
                "scene_id": "LC09_TEST_003",
                "lst_c": "35",
                "ndvi": "0.3",
                "ndbi": "0.2",
                "mndwi": "-0.1",
                "valid_pixel_fraction": "0.7",
                "cloud_cover_pct": "10",
            }
        ],
        ENV_FIELDS,
    )
    with pytest.raises(SatelliteIngestionError):
        ingest_landsat_observations(grid, dataset, grid_version="TEST-1KM-V1")


def _artifact(tmp_path, *, rows=120, metrics=None):
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    (artifact / "model.joblib").write_bytes(b"placeholder-not-loaded-by-registry")
    (artifact / "metrics.json").write_text(
        json.dumps(
            metrics
            if metrics is not None
            else {
                "target": "lst_c",
                "mae_c": 1.8,
                "rmse_c": 2.4,
                "r2": 0.72,
                "n_test_rows": rows,
                "test_start": "2025-01-01",
                "split": "chronological_holdout",
            }
        ),
        encoding="utf-8",
    )
    (artifact / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "lst-test-001",
                "dataset": {
                    "start_date": "2024-01-01",
                    "end_date": "2025-06-30",
                    "sha256": "a" * 64,
                    "rows": 5000,
                },
                "feature_columns": ["ndvi", "ndbi"],
                "config": {},
                "limitations": ["LST is not air temperature."],
            }
        ),
        encoding="utf-8",
    )
    return artifact


def test_register_artifact_requires_evaluation(tmp_path):
    bad = tmp_path / "bad"
    bad.mkdir()
    with pytest.raises(HeatModelError):
        register_artifact(bad)

    artifact = _artifact(tmp_path, metrics={"mae_c": 1.0})
    with pytest.raises(HeatModelError, match="missing"):
        register_artifact(artifact)


def test_register_artifact_defaults_to_non_operational(tmp_path):
    artifact = _artifact(tmp_path)
    model = register_artifact(artifact)
    assert model.is_operational is False
    assert model.metrics["mae_c"] == 1.8
    assert model.training_period_start.isoformat() == "2024-01-01"
    assert ModelVersion.objects.count() == 1


def test_ingest_predictions_creates_complete_run(grid, tmp_path):
    artifact = _artifact(tmp_path)
    model = register_artifact(artifact, operational=True, activate=True)
    cells = list(GridCell.objects.filter(definition__area=grid)[:2])
    dataset = _write_csv(
        tmp_path / "predictions.csv",
        [
            {
                "cell_code": cell.code,
                "observed_on": "2025-06-15",
                "predicted_lst_c": "37.25",
            }
            for cell in cells
        ],
        ["cell_code", "observed_on", "predicted_lst_c"],
    )
    run = ingest_predictions(grid, model, dataset, grid_version="TEST-1KM-V1")
    assert run.status == PredictionRunStatus.COMPLETE
    assert CellPrediction.objects.filter(run=run).count() == 2
    assert run.metadata["written"] == 2


def test_ingest_predictions_refuses_unscored_model(grid, tmp_path):
    model = ModelVersion.objects.create(
        name="unscored",
        version="0",
        algorithm="xgboost",
        target="lst_c",
        dataset_version="x",
        metrics={},
    )
    dataset = _write_csv(
        tmp_path / "predictions.csv",
        [{"cell_code": "x", "observed_on": "2025-06-15", "predicted_lst_c": "37"}],
        ["cell_code", "observed_on", "predicted_lst_c"],
    )
    with pytest.raises(HeatModelError, match="no evaluation metrics"):
        ingest_predictions(grid, model, dataset)


def test_heat_api_reports_predictions_with_disclaimer(api_client, grid, tmp_path):
    artifact = _artifact(tmp_path)
    model = register_artifact(artifact, operational=True, activate=True)
    cell = GridCell.objects.filter(definition__area=grid).first()
    dataset = _write_csv(
        tmp_path / "predictions.csv",
        [{"cell_code": cell.code, "observed_on": "2025-06-15", "predicted_lst_c": "37.25"}],
        ["cell_code", "observed_on", "predicted_lst_c"],
    )
    ingest_predictions(grid, model, dataset, grid_version="TEST-1KM-V1")

    response = api_client.get("/api/v1/heat/predictions/?area=kolkata")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "AVAILABLE"
    assert body["count"] == 1
    assert "not an air-temperature measurement" in body["disclaimer"]

    info = api_client.get("/api/v1/heat/model-info/").json()
    assert info["state"] == "AVAILABLE"
    assert info["active_model"]["metrics"]["mae_c"] == 1.8


def test_heat_api_is_unavailable_without_a_model(api_client, area):
    response = api_client.get("/api/v1/heat/predictions/?area=kolkata")
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "UNAVAILABLE"
    assert body["run"] is None
    assert PredictionRun.objects.count() == 0
