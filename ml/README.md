# Heat and environmental ML

This package contains the reproducible pipeline for the land-surface temperature
(LST) and heat-risk models. It is deliberately small and command-line driven so
that every artefact can be traced back to a dataset, a code revision and a
metrics file.

## Honest status

A surface-heat model has been trained on real Landsat data for Kolkata
(`reports/land_surface_heat.json`). On 17 later dates its error was 1.54 °C,
against 3.08 °C for each cell's past average for that month. It uses
same-scene satellite features, so it fills gaps rather than forecasts.
Consequently:

- it is registered as non-operational and inactive;
- `/api/v1/heat/predictions/` returns `UNAVAILABLE`;
- the data and artifacts stay out of git, so rerun the export to reproduce them.

Nothing in this package generates synthetic observations or placeholder
metrics. `train` and `evaluate` refuse to run when the dataset is absent or too
small.

## Pipeline

```
GEE export  ->  dataset CSV/GeoJSON  ->  feature validation  ->  train
                                                              ->  artifacts/<run>/
                                                                   model.joblib
                                                                   metrics.json
                                                                   manifest.json
                                                              ->  register in Django
                                                              ->  predict -> ingest
```

1. **Export observations** (`python -m src.heat.pc_landsat_export`)

   This reads Landsat from Microsoft Planetary Computer and needs no account.
   It drops physically impossible readings. The older Earth Engine exporter,
   described next, is still available if you have credentials.

   Uses Landsat 8/9 Collection 2 Level 2 surface temperature and surface
   reflectance. LST is derived exactly as documented by USGS:

   ```
   LST_C = ST_B10 * 0.00341802 + 149.0 - 273.15
   ```

   NDVI, NDBI and MNDWI are computed from surface-reflectance bands. Pixels are
   masked for cloud, cloud shadow and dilated cloud using `QA_PIXEL`. Each
   scene is aggregated to the 1 km grid cells with `reduceRegions`. The result
   is a table with one row per cell per scene.

   ```powershell
   python -m src.heat.gee_landsat_export `
     --grid-asset projects/your-project/assets/kolkata_grid_1km_v1 `
     --start 2023-01-01 --end 2025-12-31 `
     --output data/raw/kolkata_lst_2023_2025.csv
   ```

   The command requires:
   - `GEE_PROJECT_ID`
   - `GEE_SERVICE_ACCOUNT_EMAIL`
   - `GEE_SERVICE_ACCOUNT_KEY_FILE`

   If any are missing it exits with a clear message and writes nothing.

2. **Train** (`python -m src.heat.train`)

   Validates columns, removes rows with a missing target, splits
   chronologically (latest 20% of observation dates are held out), fits an
   XGBoost regressor, evaluates on the held-out period and writes the artefact
   directory.

   ```powershell
   python -m src.heat.train --dataset data/raw/kolkata_lst_2023_2025.csv
   ```

   Gates: at least 500 rows, at least 20 distinct dates and at least 10 test
   dates. A dataset that fails these gates is rejected rather than trained on.

3. **Evaluate** (`python -m src.heat.evaluate`) recomputes metrics from a saved
   artefact and dataset. It never edits the stored metrics.

4. **Register** (`python manage.py register_heat_model`) copies the metrics and
   manifest into `ModelVersion` with `is_operational=False` by default. An
   operator must explicitly pass `--operational` after reviewing the metrics and
   limitations.

5. **Predict and ingest** (`python -m src.heat.predict` then
   `python manage.py ingest_heat_predictions`) writes cell predictions to the
   `PredictionRun` / `CellPrediction` tables.

## Waterlogging

No waterlogging model is trained yet, because there are no real labels. The inputs are ready.

1. `python -m src.waterlogging.terrain_export --grid data/raw/kolkata_grid.geojson --landsat data/raw/kolkata_lst.csv --output data/raw/kolkata_terrain.csv`
   works out elevation, height against nearby land, slope, wetness and hollows from Copernicus GLO-30.
2. `manage.py ingest_terrain --dataset ../ml/data/raw/kolkata_terrain.csv` stores it for the map and the signal.
3. `manage.py export_waterlogging_dataset --output ../ml/data/raw/waterlogging.csv` joins terrain, historical rain and reports.
4. `python -m src.waterlogging.train --dataset data/raw/waterlogging.csv` refuses to run below 300 flooded rows and
   30 wet dates, and keeps a model only if it beats rain alone on later dates.

GLO-30 measures the tops of surfaces, so buildings affect it. It knows nothing about drains, pumps or tides.

## Dataset contract

Required columns:

| column | meaning |
| --- | --- |
| `cell_code` | stable 1 km grid cell code from the Django grid version |
| `observed_on` | scene date (`YYYY-MM-DD`) |
| `scene_id` | Landsat scene identifier |
| `lst_c` | target: land-surface temperature in °C |
| `ndvi` | vegetation index |
| `ndbi` | built-up index |
| `mndwi` | water index |
| `valid_pixel_fraction` | fraction of valid 30 m pixels inside the cell |
| `cloud_cover_pct` | scene cloud cover |
| `centroid_lat`, `centroid_lon` | cell centroid (EPSG:4326) |
| `elevation_m` | SRTM elevation summarised per cell |

Rows with `valid_pixel_fraction < 0.5` are dropped. This threshold is recorded
in the manifest.

## Why the target is LST, not air temperature

Landsat thermal bands measure land-surface temperature. Air temperature is
measured by weather stations and is not interchangeable with LST. The product
always labels predictions as estimated LST and never presents them as an
official heat warning or air-temperature measurement.

## Limitations

- Landsat has a 16-day revisit and cloud cover removes many observations.
- The 1 km grid is an aggregation unit; thermal native resolution is 100 m.
- Training data availability determines which seasons and years are
  represented.
- Metrics from a chronological hold-out describe that period only. They are not
  a guarantee of future performance.
- No fairness or spatial-leakage audit exists until a real dataset is exported.

## Tests

```powershell
python -m pytest tests -q
```

Tests cover feature validation, chronological splitting, manifest creation and
the refusal paths. They do not assert any model score.

## Next-day models

These are the only models with real labels today. Run from `ml/`:

```bash
python -m src.forecast.dataset --end YYYY-MM-DD
python -m src.forecast.train
```

Copy the new `metrics.json` to `reports/next_day.json` to update the `/models` page.
