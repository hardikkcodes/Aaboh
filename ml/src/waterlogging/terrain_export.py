"""Work out real terrain for each 1 km grid cell, as inputs for waterlogging.

Reads the Copernicus GLO-30 elevation model from Microsoft Planetary Computer, which
needs no account. GLO-30 measures the top of surfaces, so dense buildings raise it;
cell medians soften that but don't remove it. This describes the land. It says nothing
about drains or pumps, and it is not a flood prediction.

Example
-------
    python -m src.waterlogging.terrain_export --grid data/raw/kolkata_grid.geojson \
        --landsat data/raw/kolkata_lst.csv --output data/raw/kolkata_terrain.csv
"""

from __future__ import annotations

import argparse
import heapq
import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.features import rasterize
from rasterio.merge import merge
from rasterio.warp import Resampling, calculate_default_transform, reproject
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform

STAC_SEARCH = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS_TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/cop-dem-glo-30"
DEM_SOURCE = "Copernicus GLO-30"
GRID_EPSG = 32645
RESOLUTION_M = 90
MARGIN_DEGREES = 0.08
NEIGHBOUR_RADIUS_M = 3000
DEPRESSION_DEPTH_M = 0.5
TIMEOUT_SECONDS = 60
# Assumed weights: there are no flood labels yet to learn them from.
WEIGHTS = {"low_ground": 0.35, "depressions": 0.3, "wetness": 0.2, "built_up": 0.15}
NEIGHBOURS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def load_dem(bbox: list[float]) -> tuple[np.ndarray, object]:
    """Elevation in metres on a regular grid in the project's coordinate system."""
    response = requests.post(
        STAC_SEARCH,
        json={"collections": ["cop-dem-glo-30"], "bbox": bbox, "limit": 10},
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    token = requests.get(SAS_TOKEN, timeout=TIMEOUT_SECONDS).json()["token"]
    sources = [rasterio.open(f"{item['assets']['data']['href']}?{token}") for item in response.json()["features"]]
    if not sources:
        raise SystemExit("No elevation tiles cover this grid.")
    mosaic, transform = merge(sources, bounds=tuple(bbox))
    crs = sources[0].crs
    height, width = mosaic.shape[1:]
    target, target_width, target_height = calculate_default_transform(
        crs, f"EPSG:{GRID_EPSG}", width, height,
        left=bbox[0], bottom=bbox[1], right=bbox[2], top=bbox[3], resolution=RESOLUTION_M,
    )
    dem = np.zeros((target_height, target_width), dtype="float32")
    reproject(
        mosaic[0], dem, src_transform=transform, src_crs=crs,
        dst_transform=target, dst_crs=f"EPSG:{GRID_EPSG}", resampling=Resampling.average,
    )
    for source in sources:
        source.close()
    return dem, target


def fill_depressions(dem: np.ndarray) -> np.ndarray:
    """Priority-flood: raise each hollow to the level water would spill out of it."""
    rows, columns = dem.shape
    filled = dem.astype("float64").copy()
    seen = np.zeros(dem.shape, dtype=bool)
    heap: list[tuple[float, int, int]] = []
    for row in range(rows):
        for column in (0, columns - 1):
            heap.append((filled[row, column], row, column))
            seen[row, column] = True
    for column in range(columns):
        for row in (0, rows - 1):
            if not seen[row, column]:
                heap.append((filled[row, column], row, column))
                seen[row, column] = True
    heapq.heapify(heap)
    while heap:
        level, row, column = heapq.heappop(heap)
        for d_row, d_column in NEIGHBOURS:
            r, c = row + d_row, column + d_column
            if 0 <= r < rows and 0 <= c < columns and not seen[r, c]:
                seen[r, c] = True
                # A tiny rise keeps flat filled areas draining in one direction.
                filled[r, c] = max(filled[r, c], level + 1e-3)
                heapq.heappush(heap, (filled[r, c], r, c))
    return filled


def flow_accumulation(filled: np.ndarray) -> np.ndarray:
    """How many cells drain through each cell, following the steepest way down."""
    rows, columns = filled.shape
    accumulation = np.ones(filled.shape, dtype="float64")
    for index in np.argsort(filled, axis=None)[::-1]:
        row, column = int(index // columns), int(index % columns)
        best_drop, target = 0.0, None
        for d_row, d_column in NEIGHBOURS:
            r, c = row + d_row, column + d_column
            if 0 <= r < rows and 0 <= c < columns:
                drop = (filled[row, column] - filled[r, c]) / np.hypot(d_row, d_column)
                if drop > best_drop:
                    best_drop, target = drop, (r, c)
        if target:
            accumulation[target] += accumulation[row, column]
    return accumulation


def load_cells(path: Path) -> list[dict]:
    from pyproj import Transformer

    project = Transformer.from_crs("EPSG:4326", f"EPSG:{GRID_EPSG}", always_xy=True).transform
    cells = []
    for number, feature in enumerate(json.loads(path.read_text(encoding="utf-8"))["features"], start=1):
        geometry = shape(feature["geometry"])
        cells.append(
            {
                "number": number,
                "code": feature["properties"]["cell_code"],
                "geometry": shapely_transform(project, geometry),
                "bounds": geometry.bounds,
            }
        )
    return cells


def percentile(series: pd.Series, *, ascending: bool = True) -> pd.Series:
    return series.rank(pct=True, ascending=ascending).fillna(0.5)


def score(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame["susceptibility"] = (
        WEIGHTS["low_ground"] * percentile(frame["relative_elevation_m"], ascending=False)
        + WEIGHTS["depressions"] * percentile(frame["depression_fraction"])
        + WEIGHTS["wetness"] * percentile(frame["twi"])
        + WEIGHTS["built_up"] * percentile(frame["built_up_index"])
    ).round(3)
    high, medium = frame["susceptibility"].quantile([0.8, 0.5])
    frame["terrain_class"] = np.select(
        [frame["susceptibility"] >= high, frame["susceptibility"] >= medium], ["high", "medium"], "low"
    )
    frame["dem_source"] = DEM_SOURCE
    return frame


def build(cells: list[dict], landsat: Path | None) -> pd.DataFrame:
    west = min(cell["bounds"][0] for cell in cells) - MARGIN_DEGREES
    south = min(cell["bounds"][1] for cell in cells) - MARGIN_DEGREES
    east = max(cell["bounds"][2] for cell in cells) + MARGIN_DEGREES
    north = max(cell["bounds"][3] for cell in cells) + MARGIN_DEGREES
    dem, transform = load_dem([west, south, east, north])
    filled = fill_depressions(dem)
    accumulation = flow_accumulation(filled)
    gradient_y, gradient_x = np.gradient(dem.astype("float64"), RESOLUTION_M)
    slope = np.hypot(gradient_x, gradient_y)
    wetness = np.log((accumulation * RESOLUTION_M) / np.maximum(slope, 1e-3))
    depressions = (filled - dem) >= DEPRESSION_DEPTH_M
    labels = rasterize(
        ((cell["geometry"], cell["number"]) for cell in cells),
        out_shape=dem.shape, transform=transform, fill=0, dtype="int32",
    )

    rows = []
    for cell in cells:
        inside = labels == cell["number"]
        if not inside.any():
            continue
        rows.append(
            {
                "cell_code": cell["code"],
                "elevation_m": round(float(np.median(dem[inside])), 2),
                "slope_deg": round(float(np.degrees(np.arctan(np.median(slope[inside])))), 3),
                "twi": round(float(np.median(wetness[inside])), 3),
                "depression_fraction": round(float(depressions[inside].mean()), 4),
                "x": cell["geometry"].centroid.x,
                "y": cell["geometry"].centroid.y,
            }
        )
    frame = pd.DataFrame(rows)
    gaps = np.hypot(
        frame["x"].to_numpy()[:, None] - frame["x"].to_numpy(),
        frame["y"].to_numpy()[:, None] - frame["y"].to_numpy(),
    )
    elevations = frame["elevation_m"].to_numpy()
    frame["relative_elevation_m"] = [
        round(float(elevations[i] - np.median(elevations[gaps[i] <= NEIGHBOUR_RADIUS_M])), 2)
        for i in range(len(frame))
    ]
    frame = frame.drop(columns=["x", "y"])
    if landsat and landsat.exists():
        built_up = pd.read_csv(landsat).groupby("cell_code")["ndbi"].median().round(4)
        frame["built_up_index"] = frame["cell_code"].map(built_up)
    else:
        frame["built_up_index"] = np.nan
    return score(frame)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", required=True)
    parser.add_argument("--landsat")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    frame = build(load_cells(Path(args.grid)), Path(args.landsat) if args.landsat else None)
    frame.to_csv(args.output, index=False)
    print(f"{len(frame)} cells written to {args.output}")
    print(frame[["elevation_m", "relative_elevation_m", "slope_deg", "twi", "depression_fraction", "susceptibility"]].describe().round(2).to_string())
    print(frame["terrain_class"].value_counts().to_string())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
