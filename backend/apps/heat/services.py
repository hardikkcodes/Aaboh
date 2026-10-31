"""Registration and ingestion services for heat model artefacts.

This module deliberately performs no training. It accepts only artefacts that
already contain a metrics file produced by ``ml/src/heat/train.py`` and refuses
to register an unevaluated model as operational.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, date, datetime, time
from pathlib import Path

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.locations.models import Area, GridCell

from .models import CellPrediction, ModelTask, ModelVersion, PredictionRun, PredictionRunStatus


class HeatModelError(Exception):
    pass


REQUIRED_METRICS = {"mae_c", "rmse_c", "r2", "n_test_rows", "test_start", "split"}


def register_artifact(artifact_dir: str | Path, *, operational: bool = False, activate: bool = False) -> ModelVersion:
    artifact = Path(artifact_dir)
    metrics_path = artifact / "metrics.json"
    manifest_path = artifact / "manifest.json"
    model_path = artifact / "model.joblib"
    for path in (metrics_path, manifest_path, model_path):
        if not path.exists():
            raise HeatModelError(f"Artifact is incomplete; missing {path.name} in {artifact}")

    with metrics_path.open(encoding="utf-8") as handle:
        metrics = json.load(handle)
    with manifest_path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    missing = REQUIRED_METRICS.difference(metrics)
    if missing:
        raise HeatModelError("Metrics file is missing: " + ", ".join(sorted(missing)))
    if int(metrics.get("n_test_rows") or 0) <= 0:
        raise HeatModelError("Metrics report no held-out rows; refusing to register.")
    if operational and not metrics.get("test_start"):
        raise HeatModelError("An operational model must have a dated evaluation period.")

    dataset = manifest.get("dataset", {})
    defaults = {
        "name": manifest.get("name") or "Kolkata land-surface temperature",
        "task": ModelTask.LST,
        "algorithm": "XGBoost regressor",
        "target": metrics.get("target", "lst_c"),
        "dataset_version": dataset.get("sha256", "")[:16] or "unknown",
        "feature_schema": {"features": manifest.get("feature_columns", [])},
        "training_period_start": _date_or_none(dataset.get("start_date")),
        "training_period_end": _date_or_none(dataset.get("end_date")),
        "metrics": metrics,
        "artifact_path": str(model_path.resolve()),
        "code_commit": manifest.get("git_commit") or "",
        "training_config": manifest.get("config", {}),
        "trained_at": timezone.now(),
        "is_operational": operational,
        "limitations": "\n".join(manifest.get("limitations", [])),
    }

    with transaction.atomic():
        if activate:
            ModelVersion.objects.filter(task=ModelTask.LST, is_active=True).update(is_active=False)
        version = manifest.get("run_id") or artifact.name
        model, created = ModelVersion.objects.update_or_create(
            name=defaults["name"],
            version=version,
            defaults=defaults,
        )
        if activate:
            model.is_active = True
            model.save(update_fields=["is_active"])
    return model


def _date_or_none(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    return parse_date(str(value))


def ingest_predictions(
    area: Area,
    model: ModelVersion,
    path: str | Path,
    *,
    grid_version: str | None = None,
) -> PredictionRun:
    dataset = Path(path)
    if not dataset.exists():
        raise HeatModelError(f"Predictions file not found: {dataset}")
    if model.task != ModelTask.LST:
        raise HeatModelError("Predictions can only be ingested for an LST model.")
    if not model.metrics:
        raise HeatModelError("The model has no evaluation metrics; refusing to serve predictions.")

    definition = (
        area.grid_definitions.filter(version=grid_version).first()
        if grid_version
        else area.grid_definitions.first()
    )
    if definition is None:
        raise HeatModelError(f"No analytical grid exists for {area.slug}.")
    cells = {cell.code: cell for cell in GridCell.objects.filter(definition=definition)}

    with dataset.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"cell_code", "observed_on", "predicted_lst_c"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise HeatModelError("Predictions file is missing: " + ", ".join(sorted(missing)))
        rows = list(reader)

    run = PredictionRun.objects.create(
        model_version=model,
        area=area,
        status=PredictionRunStatus.RUNNING,
        metadata={
            "grid_version": definition.version,
            "source_file": str(dataset),
            "row_count": len(rows),
        },
    )
    written = 0
    skipped = 0
    dates: list[date] = []
    try:
        with transaction.atomic():
            for row in rows:
                cell = cells.get((row.get("cell_code") or "").strip())
                observed_on = parse_date((row.get("observed_on") or "").strip())
                try:
                    value = float(row.get("predicted_lst_c") or "")
                except ValueError:
                    value = None
                if cell is None or observed_on is None or value is None:
                    skipped += 1
                    continue
                dates.append(observed_on)
                CellPrediction.objects.update_or_create(
                    run=run,
                    cell=cell,
                    defaults={"predicted_lst_c": value},
                )
                written += 1

        if written == 0:
            raise HeatModelError("No prediction rows matched the grid cells.")
        run.status = PredictionRunStatus.COMPLETE
        run.valid_from = datetime.combine(min(dates), time.min, tzinfo=UTC)
        run.valid_to = datetime.combine(max(dates), time.max, tzinfo=UTC)
        run.metadata = {**run.metadata, "written": written, "skipped": skipped}
        run.save(update_fields=["status", "valid_from", "valid_to", "metadata"])
        return run
    except Exception as exc:  # noqa: BLE001
        run.status = PredictionRunStatus.FAILED
        run.error_message = str(exc)[:2000]
        run.save(update_fields=["status", "error_message"])
        if isinstance(exc, HeatModelError):
            raise
        raise HeatModelError(str(exc)) from exc
