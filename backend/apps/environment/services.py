"""Ingestion of satellite-derived environmental observations.

The exporter is intentionally separate (see ``ml/src/heat/gee_landsat_export.py``)
because Google Earth Engine credentials and compute do not belong in the web
process. This service only accepts an already-exported table and preserves its
provenance. It never invents rows for missing scenes or cells.
"""

from __future__ import annotations

import csv
from datetime import UTC, date, datetime, time
from pathlib import Path

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from apps.core.models import DataSource, IngestionRun, IngestionRunStatus
from apps.environment.models import EnvironmentalObservation, SatelliteScene
from apps.locations.models import Area, GridCell


class SatelliteIngestionError(Exception):
    pass


REQUIRED_FIELDS = {
    "cell_code",
    "observed_on",
    "scene_id",
    "lst_c",
    "ndvi",
    "ndbi",
    "mndwi",
    "valid_pixel_fraction",
}
VARIABLES = ("lst_c", "ndvi", "ndbi", "mndwi")


def _float(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise SatelliteIngestionError(f"Expected a number, received {value!r}") from exc


def _acquired_at(row: dict, observed_on: date) -> tuple[datetime, bool]:
    raw = (row.get("acquired_at") or "").strip()
    if raw:
        parsed = parse_datetime(raw)
        if parsed is None:
            raise SatelliteIngestionError(f"Invalid acquired_at value: {raw!r}")
        if timezone.is_naive(parsed):
            parsed = parsed.replace(tzinfo=UTC)
        return parsed, False
    # The export did not carry an acquisition time. Store the scene date at
    # midnight UTC and flag that the time is unknown rather than inventing one.
    return datetime.combine(observed_on, time.min, tzinfo=UTC), True


def ingest_landsat_observations(
    area: Area,
    path: str | Path,
    *,
    grid_version: str | None = None,
    processing_version: str = "landsat-c2l2-v1",
    min_valid_pixel_fraction: float = 0.5,
) -> dict:
    source = DataSource.objects.filter(slug="landsat").first()
    if source is None:
        raise SatelliteIngestionError("The landsat DataSource has not been seeded.")
    dataset = Path(path)
    if not dataset.exists():
        raise SatelliteIngestionError(f"Dataset not found: {dataset}")

    definition = (
        area.grid_definitions.filter(version=grid_version).first()
        if grid_version
        else area.grid_definitions.first()
    )
    if definition is None:
        raise SatelliteIngestionError(
            f"No analytical grid exists for {area.slug}. Run bootstrap_kolkata or generate a grid first."
        )
    cells = {cell.code: cell for cell in GridCell.objects.filter(definition=definition)}
    if not cells:
        raise SatelliteIngestionError(f"Grid {definition.version} has no cells.")

    run = IngestionRun.objects.create(
        source=source,
        status=IngestionRunStatus.RUNNING,
        params={
            "area": area.slug,
            "dataset": str(dataset),
            "grid_version": definition.version,
            "processing_version": processing_version,
        },
    )
    fetched = 0
    written = 0
    skipped = 0
    scenes: dict[str, object] = {}

    try:
        with dataset.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing = REQUIRED_FIELDS.difference(reader.fieldnames or [])
            if missing:
                raise SatelliteIngestionError(
                    "Dataset is missing columns: " + ", ".join(sorted(missing))
                )
            rows = list(reader)

        with transaction.atomic():
            for row in rows:
                fetched += 1
                code = (row.get("cell_code") or "").strip()
                cell = cells.get(code)
                if cell is None:
                    skipped += 1
                    continue
                observed_on = parse_date((row.get("observed_on") or "").strip())
                if observed_on is None:
                    raise SatelliteIngestionError(
                        f"Invalid observed_on value: {row.get('observed_on')!r}"
                    )
                scene_id = (row.get("scene_id") or "").strip()
                if not scene_id:
                    raise SatelliteIngestionError("Row is missing scene_id.")
                acquired_at, time_unknown = _acquired_at(row, observed_on)

                scene = scenes.get(scene_id)
                if scene is None:
                    flags = []
                    if time_unknown:
                        flags.append("acquisition_time_unknown")
                    scene, _ = SatelliteScene.objects.update_or_create(
                        source=source,
                        scene_id=scene_id,
                        defaults={
                            "platform": "LANDSAT_8_9",
                            "collection": "C02/T1_L2",
                            "acquired_at": acquired_at,
                            "cloud_cover_pct": _float(row.get("cloud_cover_pct")),
                            "processing_level": "L2SP",
                            "metadata": {
                                "acquisition_time_unknown": time_unknown,
                                "processing_version": processing_version,
                            },
                        },
                    )
                    scenes[scene_id] = scene

                fraction = _float(row.get("valid_pixel_fraction")) or 0.0
                fraction = min(max(fraction, 0.0), 1.0)
                quality_flags = []
                if fraction < min_valid_pixel_fraction:
                    quality_flags.append("low_valid_pixel_fraction")
                if fraction == 0:
                    continue

                values = {variable: _float(row.get(variable)) for variable in VARIABLES}
                if values["lst_c"] is None:
                    skipped += 1
                    continue

                EnvironmentalObservation.objects.update_or_create(
                    scene=scene,
                    cell=cell,
                    defaults={
                        "observed_on": observed_on,
                        "valid_pixel_fraction": fraction,
                        "quality_flags": quality_flags,
                        "processing_version": processing_version,
                        **values,
                    },
                )
                written += 1

        run.status = IngestionRunStatus.SUCCESS if written else IngestionRunStatus.FAILED
        run.records_fetched = fetched
        run.records_written = written
        run.finished_at = timezone.now()
        if not written:
            run.error_message = "No usable observations were found in the dataset."
        run.save(
            update_fields=[
                "status",
                "records_fetched",
                "records_written",
                "finished_at",
                "error_message",
            ]
        )
    except Exception as exc:  # noqa: BLE001 - audit then surface
        run.status = IngestionRunStatus.FAILED
        run.records_fetched = fetched
        run.records_written = written
        run.finished_at = timezone.now()
        run.error_message = str(exc)[:2000]
        run.save(
            update_fields=[
                "status",
                "records_fetched",
                "records_written",
                "finished_at",
                "error_message",
            ]
        )
        if isinstance(exc, SatelliteIngestionError):
            raise
        raise SatelliteIngestionError(str(exc)) from exc

    if not written:
        raise SatelliteIngestionError(
            "No usable observations were found. Check the grid version, cell codes and LST values."
        )
    return {
        "fetched": fetched,
        "written": written,
        "skipped": skipped,
        "scenes": len(scenes),
        "grid_version": definition.version,
        "run_id": str(run.id),
        "state": "AVAILABLE" if written else "UNAVAILABLE",
    }
