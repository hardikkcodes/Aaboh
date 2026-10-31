"""Export real Landsat observations to the 1 km grid without Google Earth Engine.

Reads Landsat Collection 2 Level 2 from Microsoft Planetary Computer, which needs no
account. The output has the same columns as the Earth Engine export, so it works with
``ingest_landsat_observations`` and the training pipeline.

Example
-------
    python -m src.heat.pc_landsat_export --grid data/raw/grid.geojson \
        --start 2023-01-01 --end 2026-10-20 --output data/raw/kolkata_lst.csv
"""

from __future__ import annotations

import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import requests
from rasterio.errors import RasterioError
from rasterio.features import rasterize
from rasterio.windows import from_bounds
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform

from .config import (
    KELVIN_TO_CELSIUS,
    SR_OFFSET,
    SR_SCALE,
    ST_B10_OFFSET_KELVIN,
    ST_B10_SCALE,
)

STAC_SEARCH = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
SAS_TOKEN = "https://planetarycomputer.microsoft.com/api/sas/v1/token/landsat-c2-l2"
ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"
BANDS = ("lwir11", "qa_pixel", "green", "red", "nir08", "swir16")
MAX_CLOUD_COVER = 40
GRID_EPSG = 32645
WRS_ROW = "044"
PARALLEL_SCENES = 6
MIN_LST_C = -30
MAX_LST_C = 80
TOKEN_LIFETIME = timedelta(minutes=20)

_token_lock = threading.Lock()
_shared_token = ""
_token_expires = datetime.min.replace(tzinfo=UTC)
# QA_PIXEL bits: dilated cloud, cloud, cloud shadow.
CLOUD_BITS = (1 << 1) | (1 << 3) | (1 << 4)
PIXEL_AREA_M2 = 900
TIMEOUT_SECONDS = 60
ELEVATION_BATCH = 100


def search_scenes(bbox: list[float], start: str, end: str) -> list[dict]:
    scenes: list[dict] = []
    body: dict | None = {
        "collections": ["landsat-c2-l2"],
        "bbox": bbox,
        "datetime": f"{start}/{end}",
        "query": {"eo:cloud_cover": {"lt": MAX_CLOUD_COVER}, "platform": {"in": ["landsat-8", "landsat-9"]}},
        "limit": 100,
    }
    while body:
        response = requests.post(STAC_SEARCH, json=body, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        page = response.json()
        scenes.extend(page["features"])
        following = next((link for link in page.get("links", []) if link.get("rel") == "next"), None)
        body = following.get("body") if following else None
    # Row 44 alone covers the whole city, so the overlapping row would only repeat it.
    covering = [item for item in scenes if item["properties"].get("landsat:wrs_row") == WRS_ROW]
    return sorted(covering, key=lambda item: item["properties"]["datetime"])


def _token() -> str:
    """One token shared by all workers: asking for one per scene gets rate-limited."""
    global _shared_token, _token_expires
    with _token_lock:
        if datetime.now(UTC) >= _token_expires:
            response = requests.get(SAS_TOKEN, timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            _shared_token = response.json()["token"]
            _token_expires = datetime.now(UTC) + TOKEN_LIFETIME
        return _shared_token


def _read(href: str, token: str, bounds: tuple[float, ...]) -> tuple[np.ndarray, object]:
    with rasterio.open(f"{href}?{token}") as source:
        if source.crs.to_epsg() != GRID_EPSG:
            raise ValueError(f"Scene is in EPSG:{source.crs.to_epsg()}, not the grid's EPSG:{GRID_EPSG}")
        window = from_bounds(*bounds, transform=source.transform).round_offsets().round_lengths()
        return source.read(1, window=window, boundless=True, fill_value=0), source.window_transform(window)


def cell_elevations(cells: list[dict]) -> dict[str, float]:
    elevations: dict[str, float] = {}
    for start in range(0, len(cells), ELEVATION_BATCH):
        batch = cells[start : start + ELEVATION_BATCH]
        response = requests.get(
            ELEVATION_URL,
            params={
                "latitude": ",".join(f"{cell['lat']:.4f}" for cell in batch),
                "longitude": ",".join(f"{cell['lon']:.4f}" for cell in batch),
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        elevations.update(zip((cell["code"] for cell in batch), response.json()["elevation"], strict=True))
    return elevations


def load_grid(path: Path) -> list[dict]:
    from pyproj import Transformer

    project = Transformer.from_crs("EPSG:4326", "EPSG:32645", always_xy=True).transform
    cells = []
    for feature in json.loads(path.read_text(encoding="utf-8"))["features"]:
        properties = feature["properties"]
        geometry = shape(feature["geometry"])
        cells.append(
            {
                "code": properties["cell_code"],
                "lat": geometry.centroid.y,
                "lon": geometry.centroid.x,
                "utm": shapely_transform(project, geometry),
            }
        )
    return cells


def summarise_scene(item: dict, cells: list[dict], token: str) -> list[dict]:
    """One row per grid cell: mean values over cloud-free pixels."""
    corners = np.array([cell["utm"].bounds for cell in cells])
    bounds = (corners[:, 0].min(), corners[:, 1].min(), corners[:, 2].max(), corners[:, 3].max())
    assets = item["assets"]
    arrays = {}
    transform = None
    for band in BANDS:
        arrays[band], transform = _read(assets[band]["href"], token, bounds)

    shapes = [(cell["utm"], index + 1) for index, cell in enumerate(cells)]
    labels = rasterize(shapes, out_shape=arrays["qa_pixel"].shape, transform=transform, fill=0, dtype="int32")
    clear = (arrays["qa_pixel"] & CLOUD_BITS == 0) & (arrays["qa_pixel"] != 0) & (arrays["lwir11"] > 0)
    reflectance = {
        band: arrays[band].astype("float64") * SR_SCALE + SR_OFFSET for band in ("green", "red", "nir08", "swir16")
    }
    with np.errstate(divide="ignore", invalid="ignore"):
        values = {
            "lst_c": arrays["lwir11"].astype("float64") * ST_B10_SCALE + ST_B10_OFFSET_KELVIN - KELVIN_TO_CELSIUS,
            "ndvi": (reflectance["nir08"] - reflectance["red"]) / (reflectance["nir08"] + reflectance["red"]),
            "ndbi": (reflectance["swir16"] - reflectance["nir08"]) / (reflectance["swir16"] + reflectance["nir08"]),
            "mndwi": (reflectance["green"] - reflectance["swir16"]) / (reflectance["green"] + reflectance["swir16"]),
        }

    # Some scenes hold fill values that pass the QA mask, so physics has the last word.
    plausible = (values["lst_c"] >= MIN_LST_C) & (values["lst_c"] <= MAX_LST_C)
    for name in ("ndvi", "ndbi", "mndwi"):
        plausible &= np.abs(values[name]) <= 1
    usable = clear & (labels > 0) & plausible
    if not usable.any():
        return []

    size = len(cells) + 1
    counts = np.bincount(labels[usable], minlength=size)
    means = {
        name: np.bincount(labels[usable], weights=np.nan_to_num(array[usable]), minlength=size)
        / np.maximum(counts, 1)
        for name, array in values.items()
    }
    properties = item["properties"]
    observed = properties["datetime"][:10]
    rows = []
    for index, cell in enumerate(cells, start=1):
        if not counts[index]:
            continue
        rows.append(
            {
                "cell_code": cell["code"],
                "observed_on": observed,
                "acquired_at": properties["datetime"],
                "scene_id": item["id"],
                **{name: round(float(means[name][index]), 4) for name in values},
                "valid_pixel_fraction": round(
                    min(float(counts[index]) * PIXEL_AREA_M2 / cell["utm"].area, 1.0), 4
                ),
                "cloud_cover_pct": properties["eo:cloud_cover"],
                "centroid_lat": round(cell["lat"], 5),
                "centroid_lon": round(cell["lon"], 5),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export real Landsat observations with no account.")
    parser.add_argument("--grid", required=True, help="GeoJSON from manage.py export_grid_geojson")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    cells = load_grid(Path(args.grid))
    longitudes = [cell["lon"] for cell in cells]
    latitudes = [cell["lat"] for cell in cells]
    bbox = [min(longitudes), min(latitudes), max(longitudes), max(latitudes)]
    scenes = search_scenes(bbox, args.start, args.end)
    print(f"{len(scenes)} scenes for {len(cells)} cells", flush=True)

    elevations = cell_elevations(cells)
    rows: list[dict] = []
    failed = 0

    def read_scene(item: dict) -> list[dict] | None:
        try:
            return summarise_scene(item, cells, _token())
        except (RasterioError, OSError, KeyError, ValueError) as exc:
            print(f"skipped {item['id']}: {type(exc).__name__}", flush=True)
            return None

    with ThreadPoolExecutor(max_workers=PARALLEL_SCENES) as pool:
        for number, found in enumerate(pool.map(read_scene, scenes), start=1):
            if found is None:
                failed += 1
                continue
            rows.extend(found)
            print(f"{number}/{len(scenes)} {len(found)} cells", flush=True)

    frame = pd.DataFrame(rows)
    frame["elevation_m"] = frame["cell_code"].map(elevations)
    # Overlapping scenes share a date. Keep each cell's clearest view.
    frame = (
        frame.sort_values("valid_pixel_fraction", ascending=False)
        .drop_duplicates(["cell_code", "observed_on"])
        .sort_values(["observed_on", "cell_code"])
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    print(f"wrote {len(frame)} rows on {frame['observed_on'].nunique()} dates, {failed} scenes skipped: {output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
