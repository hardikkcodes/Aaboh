# Heat and environmental ML

This package contains the reproducible pipeline for the land-surface temperature
(LST) and heat-risk models. It is deliberately small and command-line driven so
that every artefact can be traced back to a dataset, a code revision and a
metrics file.

## Honest status

The pipeline is implemented but **no model has been trained for Kolkata** as of
the current repository state. There is no labelled Landsat observation dataset
in the repository, because exporting one requires Google Earth Engine
credentials (`GEE_PROJECT_ID`, `GEE_SERVICE_ACCOUNT_EMAIL`,
`GEE_SERVICE_ACCOUNT_KEY_FILE`) plus an Earth Engine asset containing the 1 km
analytical grid. Consequently:

- `ml/artifacts/` is empty;
- `/api/v1/heat/predictions/` returns `UNAVAILABLE`;
- `/api/v1/heat/model-info/` returns `UNAVAILABLE`;
- no metrics are displayed anywhere in the product.

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

1. **Export observations** (`python -m src.heat.gee_landsat_export`)

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
