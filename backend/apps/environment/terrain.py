"""Stored terrain for each grid cell, and the waterlogging training table built on it."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from apps.incidents.models import IncidentCategory, IncidentReport
from apps.locations.models import Area, GridCell
from apps.weather.models import WeatherKind, WeatherRecord

from .models import CellTerrain

NUMBERS = (
    "elevation_m",
    "relative_elevation_m",
    "slope_deg",
    "twi",
    "depression_fraction",
    "built_up_index",
    "susceptibility",
)
WET_DAY_MM = 10
WATER_CATEGORIES = {IncidentCategory.WATERLOGGING, IncidentCategory.FLOODING}
DATASET_COLUMNS = [
    "date",
    "cell_code",
    "rain_1d_mm",
    "rain_3d_mm",
    "elevation_m",
    "relative_elevation_m",
    "slope_deg",
    "twi",
    "depression_fraction",
    "built_up_index",
    "flooded",
]


def _number(value: str) -> float | None:
    return float(value) if value not in ("", None) else None


def ingest_terrain(area: Area, path: str | Path) -> int:
    cells = {cell.code: cell for cell in GridCell.objects.filter(area=area)}
    written = 0
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            cell = cells.get(row["cell_code"])
            if cell is None:
                continue
            CellTerrain.objects.update_or_create(
                cell=cell,
                defaults={
                    **{name: _number(row.get(name)) for name in NUMBERS},
                    "terrain_class": row["terrain_class"],
                    "dem_source": row["dem_source"],
                },
            )
            written += 1
    return written


def nearest_terrain(area: Area, latitude: float, longitude: float) -> CellTerrain | None:
    terrain = CellTerrain.objects.filter(cell__area=area.data_area).select_related("cell")
    return min(
        terrain,
        key=lambda item: (item.cell.centroid_lat - latitude) ** 2 + (item.cell.centroid_lon - longitude) ** 2,
        default=None,
    )


def daily_rain(area: Area) -> dict:
    rows = WeatherRecord.objects.filter(
        location__area=area.data_area, kind=WeatherKind.DAILY, precipitation_mm__isnull=False
    ).values_list("valid_time", "precipitation_mm")
    return {when.date(): amount for when, amount in rows}


def waterlogging_rows(area: Area) -> list[dict]:
    """One row per grid cell per wet day. Reports decide the label; nothing is made up."""
    terrain = list(CellTerrain.objects.filter(cell__area=area).select_related("cell"))
    rain = daily_rain(area)
    flooded = defaultdict(set)
    reports = IncidentReport.objects.filter(area=area, category__in=WATER_CATEGORIES, is_public=True)
    for report in reports:
        nearest = nearest_terrain(area, report.latitude, report.longitude)
        if nearest:
            flooded[report.occurred_at.date()].add(nearest.cell_id)

    rows = []
    for day, amount in sorted(rain.items()):
        if amount < WET_DAY_MM:
            continue
        recent = sum(rain.get(day - timedelta(days=back), 0) for back in range(3))
        for item in terrain:
            rows.append(
                {
                    "date": day.isoformat(),
                    "cell_code": item.cell.code,
                    "rain_1d_mm": amount,
                    "rain_3d_mm": round(recent, 2),
                    "elevation_m": item.elevation_m,
                    "relative_elevation_m": item.relative_elevation_m,
                    "slope_deg": item.slope_deg,
                    "twi": item.twi,
                    "depression_fraction": item.depression_fraction,
                    "built_up_index": item.built_up_index,
                    "flooded": int(item.cell_id in flooded[day]),
                }
            )
    return rows
