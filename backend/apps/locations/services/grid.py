from __future__ import annotations

import math
from dataclasses import dataclass

from django.db import transaction
from shapely.geometry import Point, box

from apps.core.geometry import (
    UTM_KOLKATA,
    geodesic_area_km2,
    geometry_to_json,
    parse_geometry,
    project_to_utm,
    project_to_wgs84,
)

from ..models import Area, GridCell, GridDefinition

DEFAULT_GRID_VERSION = "KMC-1KM-V1"
DEFAULT_CELL_SIZE_M = 1000
MIN_COVERAGE_FRACTION = 0.02


@dataclass(frozen=True)
class GridGenerationResult:
    definition: GridDefinition
    cells_created: int
    cells_considered: int


def _code(area: Area, version: str, row: int, col: int) -> str:
    return f"{area.slug.upper().replace('-', '')}-{version}-R{row:03d}-C{col:03d}"


def generate_grid(
    area: Area,
    *,
    version: str = DEFAULT_GRID_VERSION,
    cell_size_m: int = DEFAULT_CELL_SIZE_M,
) -> GridGenerationResult:
    """Create (or recreate) a deterministic grid aligned to the UTM kilometre origin.

    Re-running with the same inputs produces identical row/column indices, codes
    and geometry. Cells whose intersection with the study boundary is below
    ``MIN_COVERAGE_FRACTION`` are excluded.
    """
    if cell_size_m <= 0:
        raise ValueError("cell_size_m must be positive.")

    boundary = parse_geometry(area.boundary)
    boundary_utm = project_to_utm(boundary)
    min_x, min_y, max_x, max_y = boundary_utm.bounds

    origin_x = math.floor(min_x / cell_size_m) * cell_size_m
    origin_y = math.floor(min_y / cell_size_m) * cell_size_m
    max_col = math.ceil((max_x - origin_x) / cell_size_m)
    max_row = math.ceil((max_y - origin_y) / cell_size_m)

    full_cell_area = cell_size_m * cell_size_m
    prepared: list[dict] = []
    considered = 0

    for row in range(max_row):
        for col in range(max_col):
            considered += 1
            x0 = origin_x + col * cell_size_m
            y0 = origin_y + row * cell_size_m
            square = box(x0, y0, x0 + cell_size_m, y0 + cell_size_m)
            if not square.intersects(boundary_utm):
                continue
            clipped = square.intersection(boundary_utm)
            if clipped.is_empty:
                continue
            coverage = clipped.area / full_cell_area
            if coverage < MIN_COVERAGE_FRACTION:
                continue
            clipped_wgs84 = project_to_wgs84(clipped)
            full_wgs84 = project_to_wgs84(square)
            # Cell centroid is the deterministic centre of the full 1 km square.
            cx, cy = x0 + cell_size_m / 2, y0 + cell_size_m / 2
            centre = project_to_wgs84(Point(cx, cy))
            prepared.append(
                {
                    "code": _code(area, version, row, col),
                    "row": row,
                    "col": col,
                    "geometry": geometry_to_json(clipped_wgs84),
                    "full_geometry": geometry_to_json(full_wgs84),
                    "centroid": {"type": "Point", "coordinates": [centre.x, centre.y]},
                    "centroid_lat": centre.y,
                    "centroid_lon": centre.x,
                    "coverage_fraction": round(coverage, 6),
                    "area_km2": round(geodesic_area_km2(clipped_wgs84), 6),
                }
            )

    if not prepared:
        raise ValueError("No grid cells intersect the study area boundary.")

    with transaction.atomic():
        definition, _ = GridDefinition.objects.update_or_create(
            area=area,
            version=version,
            defaults={
                "cell_size_m": cell_size_m,
                "crs": UTM_KOLKATA,
                "origin_x": origin_x,
                "origin_y": origin_y,
                "cell_count": len(prepared),
                "parameters": {
                    "min_coverage_fraction": MIN_COVERAGE_FRACTION,
                    "alignment": "floor_to_cell_size_in_projected_crs",
                    "generator": "apps.locations.services.grid",
                    "generator_version": "1.0",
                },
            },
        )
        definition.cells.all().delete()
        GridCell.objects.bulk_create(
            [
                GridCell(definition=definition, area=area, **payload)
                for payload in prepared
            ],
            batch_size=200,
        )

    return GridGenerationResult(
        definition=definition, cells_created=len(prepared), cells_considered=considered
    )
