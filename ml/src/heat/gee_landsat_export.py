"""Export Landsat 8/9 Collection 2 observations to the 1 km analytical grid.

This is a real Google Earth Engine script. It requires an Earth Engine project,
a service account and a FeatureCollection asset containing the 1 km grid with a
``cell_code`` property. It does not fabricate data: when credentials or the grid
asset are missing it exits without writing an output file.

Example
-------
    python -m src.heat.gee_landsat_export \
        --grid-asset projects/my-project/assets/kolkata_grid_1km_v1 \
        --start 2023-01-01 --end 2025-12-31 \
        --output data/raw/kolkata_lst_2023_2025.csv
"""

from __future__ import annotations

import argparse
import time
from datetime import UTC, datetime
from pathlib import Path

from .config import (
    KELVIN_TO_CELSIUS,
    KOLKATA_BBOX,
    SR_OFFSET,
    SR_SCALE,
    ST_B10_OFFSET_KELVIN,
    ST_B10_SCALE,
    fail,
    require_reason,
)

SELECTORS = [
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
    "centroid_lat",
    "centroid_lon",
    "elevation_m",
]


def _import_ee():
    try:
        import ee  # noqa: PLC0415 - optional dependency
    except ImportError:
        fail(
            "earthengine-api is not installed. Run `pip install -r ml/requirements.txt`."
        )
    return ee


def initialise(project: str, email: str, key_file: str):
    ee = _import_ee()
    credentials = ee.ServiceAccountCredentials(email, key_file)
    ee.Initialize(credentials, project=project)
    return ee


def _mask_and_indices(ee, image):
    qa = image.select("QA_PIXEL")
    cloud = qa.bitwiseAnd(1 << 3).neq(0)
    shadow = qa.bitwiseAnd(1 << 4).neq(0)
    dilated = qa.bitwiseAnd(1 << 1).neq(0)
    clear = cloud.Or(shadow).Or(dilated).Not()

    optical = image.select(["SR_B3", "SR_B4", "SR_B5", "SR_B6"]).multiply(SR_SCALE).add(SR_OFFSET)
    green, red, nir, swir1 = (
        optical.select("SR_B3"),
        optical.select("SR_B4"),
        optical.select("SR_B5"),
        optical.select("SR_B6"),
    )

    ndvi = nir.subtract(red).divide(nir.add(red)).rename("ndvi")
    ndbi = swir1.subtract(nir).divide(swir1.add(nir)).rename("ndbi")
    mndwi = green.subtract(swir1).divide(green.add(swir1)).rename("mndwi")

    lst_c = (
        image.select("ST_B10")
        .multiply(ST_B10_SCALE)
        .add(ST_B10_OFFSET_KELVIN)
        .subtract(KELVIN_TO_CELSIUS)
        .rename("lst_c")
    )

    combined = lst_c.addBands([ndvi, ndbi, mndwi]).updateMask(clear)
    return image.addBands(combined, overwrite=True)


def build_collection(ee, start: str, end: str, bbox: dict[str, float]):
    region = ee.Geometry.Rectangle([bbox["min_lon"], bbox["min_lat"], bbox["max_lon"], bbox["max_lat"]])
    landsat8 = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .filterDate(start, end)
        .filterBounds(region)
        .filter(ee.Filter.lt("CLOUD_COVER", 70))
    )
    landsat9 = (
        ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        .filterDate(start, end)
        .filterBounds(region)
        .filter(ee.Filter.lt("CLOUD_COVER", 70))
    )
    return landsat8.merge(landsat9).sort("system:time_start")


def export(
    *,
    grid_asset: str,
    start: str,
    end: str,
    output: Path,
    project: str,
    email: str,
    key_file: str,
    wait: bool = True,
    bbox: dict[str, float] | None = None,
) -> int:
    reason = require_reason("GEE_PROJECT_ID", "GEE_SERVICE_ACCOUNT_EMAIL", "GEE_SERVICE_ACCOUNT_KEY_FILE")
    if reason:
        fail(reason + ". No export was started and no output file was written.")
    if not Path(key_file).exists():
        fail(f"Service-account key file does not exist: {key_file}")
    if end <= start:
        fail("--end must be after --start")

    ee = initialise(project, email, key_file)
    grid = ee.FeatureCollection(grid_asset)
    if grid.size().getInfo() == 0:
        fail(f"Grid asset is empty: {grid_asset}")

    elevation = ee.Image("USGS/SRTMGL1_003").select("elevation").rename("elevation_m")
    collection = build_collection(ee, start, end, bbox or KOLKATA_BBOX)
    scene_count = collection.size().getInfo()
    if scene_count == 0:
        fail("No Landsat scenes matched the date range and area. Nothing to export.")

    def per_scene(image):
        prepared = _mask_and_indices(ee, image)
        scene_id = ee.String(
            ee.Algorithms.If(
                image.get("LANDSAT_PRODUCT_ID"),
                image.get("LANDSAT_PRODUCT_ID"),
                image.id(),
            )
        )
        observed_on = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd")
        acquired_at = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd'T'HH:mm:ss'Z'")
        cloud_cover = ee.Number(image.get("CLOUD_COVER"))

        reduced = (
            prepared.addBands(elevation)
            .select(["lst_c", "ndvi", "ndbi", "mndwi", "elevation_m"])
            .reduceRegions(
                collection=grid,
                reducer=ee.Reducer.mean().combine(ee.Reducer.count(), sharedInputs=True),
                scale=30,
                crs="EPSG:32645",
                tileScale=4,
            )
        )

        def annotate(feature):
            source = ee.Feature(feature)
            centroid = source.geometry().centroid(1).coordinates()
            cell_area_m2 = source.geometry().area(1)
            # Landsat thermal pixels are 100 m and the Collection 2 Level 2
            # product is delivered at 30 m. The expected count is an area-based
            # approximation, documented in the manifest, not a measured count.
            expected_pixels = cell_area_m2.divide(900.0)
            observed_pixels = ee.Number(source.get("lst_c_count"))
            fraction = ee.Number(
                ee.Algorithms.If(
                    expected_pixels.gt(0),
                    observed_pixels.divide(expected_pixels).min(1.0),
                    ee.Number(0),
                )
            )

            def mean(name):
                return source.get(name)

            return ee.Feature(source.geometry()).set(
                {
                    "cell_code": source.get("cell_code"),
                    "scene_id": scene_id,
                    "observed_on": observed_on,
                    "acquired_at": acquired_at,
                    "cloud_cover_pct": cloud_cover,
                    "centroid_lon": centroid.get(0),
                    "centroid_lat": centroid.get(1),
                    "lst_c": mean("lst_c_mean"),
                    "ndvi": mean("ndvi_mean"),
                    "ndbi": mean("ndbi_mean"),
                    "mndwi": mean("mndwi_mean"),
                    "elevation_m": mean("elevation_m_mean"),
                    "valid_pixel_fraction": fraction,
                }
            )

        annotated = reduced.map(annotate)
        return annotated.filter(ee.Filter.notNull(["lst_c"]))


    rows = ee.FeatureCollection(collection.map(per_scene)).flatten()
    description = f"kolkata_lst_{start}_{end}".replace("-", "")
    task = ee.batch.Export.table.toDrive(
        collection=rows,
        description=description,
        folder="climatesense",
        fileNamePrefix=description,
        fileFormat="CSV",
        selectors=SELECTORS,
    )
    task.start()
    print(f"started Earth Engine export task: {description} ({scene_count} scenes)")
    print("The task writes to Google Drive folder 'climatesense'. Download the CSV and place it")
    print(f"at {output} before running the training pipeline.")
    print(f"task id: {task.id}")

    if not wait:
        return 0

    print("waiting for the export task to finish (Ctrl+C to stop waiting)...")
    while True:
        status = task.status()
        state = status.get("state")
        print(f"  {datetime.now(UTC).isoformat()} {state}")
        if state in {"COMPLETED", "FAILED", "CANCELLED"}:
            break
        time.sleep(30)
    if state != "COMPLETED":
        fail(f"Earth Engine task ended in state {state}: {status.get('error_message')}")
    print("Export completed in Google Drive. Download it to the --output path.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export Landsat LST observations from Earth Engine.")
    parser.add_argument("--grid-asset", required=True, help="EE FeatureCollection asset id for the grid")
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD (exclusive in GEE)")
    parser.add_argument("--output", required=True, help="Local path where the CSV will be stored")
    parser.add_argument("--wait", action="store_true", help="Wait for the Earth Engine task to finish")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    import os

    return export(
        grid_asset=args.grid_asset,
        start=args.start,
        end=args.end,
        output=Path(args.output),
        project=os.getenv("GEE_PROJECT_ID", ""),
        email=os.getenv("GEE_SERVICE_ACCOUNT_EMAIL", ""),
        key_file=os.getenv("GEE_SERVICE_ACCOUNT_KEY_FILE", ""),
        wait=args.wait,
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
