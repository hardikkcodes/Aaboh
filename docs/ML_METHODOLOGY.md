# ML Methodology

## Status: implemented pipeline, no trained Kolkata model

The heat ML pipeline exists, is tested, and is intentionally **artifact-driven**.
As of this repository snapshot:

- `ml/artifacts/heat/` contains no artifact;
- no labelled Landsat observation dataset exists in the repository;
- no Earth Engine export has run for Kolkata;
- `ModelVersion` is empty;
- `/api/v1/heat/model-info/` and `/api/v1/heat/predictions/` return `UNAVAILABLE`;
- no metric is displayed anywhere in the product.

This is a deliberate honesty position, not an unfinished UI. Training on
synthetic data would produce a number that looks authoritative while describing
nothing real, so the code refuses to do it.

---

## 1. Prediction target

The model predicts **daytime land-surface temperature (LST) in °C** for a 1 km
analytical grid cell.

LST is retrieved from Landsat thermal bands. It is **not** air temperature, not a
wet-bulb globe temperature, not a heat index, and not an official heat warning.
Any product surface that displays it must repeat that distinction.

## 2. Data acquisition

### Export via Google Earth Engine

`ml/src/heat/gee_landsat_export.py` requires:

- `GEE_PROJECT_ID`
- `GEE_SERVICE_ACCOUNT_EMAIL`
- `GEE_SERVICE_ACCOUNT_KEY_FILE`
- an Earth Engine asset containing the 1 km grid (`--grid-asset`)

If any requirement is missing, the command exits with a clear message and writes
nothing. No placeholder export is produced.

### Collections and indices

- `LANDSAT/LC08/C02/T1_L2`
- `LANDSAT/LC09/C02/T1_L2`
- Surface temperature:
  `LST_C = ST_B10 * 0.00341802 + 149.0 - 273.15`
- Surface reflectance scaling: `SR * 0.0000275 - 0.2`
- `NDVI = (NIR - Red) / (NIR + Red)`
- `NDBI = (SWIR1 - NIR) / (SWIR1 + NIR)`
- `MNDWI = (Green - SWIR1) / (Green + SWIR1)`
- Cloud, cloud shadow and dilated cloud pixels are masked using `QA_PIXEL`.
- Each scene is reduced to grid cells with `reduceRegions`.

### Dataset contract

Required columns:

| Column | Meaning |
| --- | --- |
| `cell_code` | Stable code from the versioned Django grid |
| `observed_on` | Scene date (`YYYY-MM-DD`) |
| `acquired_at` | Acquisition timestamp (UTC) |
| `scene_id` | Landsat scene identifier |
| `lst_c` | Target: LST in °C |
| `ndvi` | Vegetation index |
| `ndbi` | Built-up index |
| `mndwi` | Water index |
| `valid_pixel_fraction` | Fraction of valid 30 m pixels inside the cell |
| `cloud_cover_pct` | Scene cloud cover |
| `centroid_lat`, `centroid_lon` | Cell centroid (EPSG:4326) |
| `elevation_m` | SRTM elevation summarised per cell |

Ingestion drops rows with `valid_pixel_fraction < 0.5` by default. This threshold
is recorded in the artifact manifest.

## 3. Feature engineering

Features are deterministic and derived only from the observation row:

- `ndvi`, `ndbi`, `mndwi`
- `elevation_m`
- `cloud_cover_pct`
- `valid_pixel_fraction`
- `centroid_lat`, `centroid_lon`
- `day_of_year_sin`, `day_of_year_cos` (seasonal cycle)
- `year_offset` (`year - 2013`, a simple temporal trend)

Why these features:

- Surface cover indices describe vegetation, built-up surfaces and water, which
  strongly affect surface heating.
- Elevation and location capture persistent geographic differences.
- Seasonal harmonics capture the annual solar cycle without a fragile
  month-category encoding.
- `year_offset` lets the model represent multi-year change, but it also means a
  model trained through 2024 should not be treated as reliable for far-future
  years.

## 4. Validation and quality gates

Before training, the pipeline:

1. Requires every contract column.
2. Parses dates and numeric fields.
3. Drops rows missing date, target, `cell_code` or `scene_id`.
4. Drops rows below `min_valid_pixel_fraction = 0.5`.
5. Rejects physically implausible values instead of clipping:
   - LST outside −30…80 °C
   - NDVI, NDBI, MNDWI outside −1…1
   - invalid latitude/longitude
6. Requires **at least 500 valid rows**.
7. Requires **at least 20 distinct observation dates**.
8. Requires **at least 10 distinct dates in the held-out period**.

If a gate fails, training stops. There is no fallback dataset.

## 5. Split strategy

The split is **chronological**, not random:

- Unique observation dates are sorted.
- The latest 20% of dates (default) form the hold-out.
- Training uses dates strictly before the cutoff; test uses dates on/after it.

This prevents future observations leaking into training. It does **not** remove
spatial autocorrelation: adjacent 1 km cells from the same scene are highly
correlated. A spatial-block or scene-level hold-out is a future improvement.

## 6. Model

`XGBRegressor` with:

```python
n_estimators=400
max_depth=4
learning_rate=0.05
subsample=0.9
colsample_bytree=0.9
objective="reg:squarederror"
tree_method="hist"
random_state=42
```

The model is a compact gradient-boosted tree ensemble suited to tabular,
non-linear environmental relationships. Hyperparameters are fixed and recorded;
no search is performed, and no result is claimed to be tuned.

## 7. Metrics

Metrics are computed only on the held-out chronological period:

| Metric | Meaning |
| --- | --- |
| `mae_c` | Mean absolute error in °C |
| `rmse_c` | Root mean squared error in °C |
| `r2` | Coefficient of determination on the held-out rows |
| `mean_error_c` | Mean signed error (prediction − actual) |
| `n_train_rows`, `n_test_rows` | Row counts |
| `n_train_dates`, `n_test_dates` | Date counts |
| `test_start` | First held-out date |
| `split` | `chronological_holdout` |

Metrics describe **that period only**. They are not an official accuracy claim
and do not transfer automatically to air temperature, other seasons, other
cities, or future years.

## 8. Artifact contract

`ml/src/heat/train.py` writes a new directory under `ml/artifacts/heat/<run-id>/`:

```
model.joblib      fitted estimator + feature list + config + target
metrics.json      evaluated metrics only
manifest.json     dataset hash, row/date counts, config, library versions,
                  git commit, limitations, artifact filename
```

The directory name is timestamped (`lst-YYYYMMDDTHHMMSSZ`). Training refuses to
overwrite an existing run directory.

`evaluate.py` recomputes metrics against a dataset and writes a separate
`evaluation.json`; it never edits `metrics.json`.

## 9. Registration and serving

Registration is a separate operator step:

```powershell
cd backend
.venv\Scripts\python.exe manage.py register_heat_model `
  --artifact ..\ml\artifacts\heat\lst-20260101T000000Z
```

- `metrics.json`, `manifest.json` and `model.joblib` must all exist.
- Required metrics: `mae_c`, `rmse_c`, `r2`, `n_test_rows`, `test_start`, `split`.
- `n_test_rows` must be positive.
- Models register as **non-operational** by default.
- `--operational` is an explicit human decision after reviewing metrics and
  limitations.
- `--activate` makes it the active LST model.

Prediction ingestion:

```powershell
python -m src.heat.predict --artifact <artifact> --dataset <features.csv> --output <predictions.csv>
cd backend
python manage.py ingest_heat_predictions --predictions ..\predictions.csv --area kolkata
```

`ingest_heat_predictions`:

- refuses models with no metrics;
- refuses models whose task is not `lst_estimation`;
- maps rows to grid cells by `cell_code`;
- skips unknown cells, invalid dates and non-numeric predictions;
- refuses a run with zero matched rows;
- creates a `PredictionRun` with `COMPLETE` or `FAILED` status and row counts.

The API only serves **completed** prediction runs and always includes a
disclaimer that predicted LST is not measured air temperature.

## 10. Reproducibility

Each manifest records:

- dataset absolute path and SHA-256;
- cleaned row count, dropped rows, date list, cell count, date range;
- full training config;
- feature order;
- split cutoff;
- Python and library versions;
- git commit (if available);
- limitations.

Given the same dataset and code, the run should be reproducible apart from
library-level nondeterminism. The dataset itself is not committed, so the
manifest hash is the link between an artifact and its training data.

## 11. Current blockers

1. **No Earth Engine credentials** (`GEE_PROJECT_ID`,
   `GEE_SERVICE_ACCOUNT_EMAIL`, `GEE_SERVICE_ACCOUNT_KEY_FILE`).
2. **No grid asset in Earth Engine**; the grid exists only in Django/SQLite.
3. **No exported observation dataset**, therefore no training run.
4. **No evaluation artifact**, therefore no registered model and no metrics.
5. **No prediction file**, therefore no completed prediction run.

Until all five are resolved with real data, the correct product behaviour is
`UNAVAILABLE`, which is what the API returns.

## 12. Limitations and responsible use

- Landsat has a 16-day revisit; clouds remove many observations, especially
  during the monsoon.
- Thermal native resolution is ~100 m; 1 km cells are aggregations.
- LST is a surface property, not air temperature or human heat stress.
- The chronological split does not address spatial autocorrelation.
- A single hold-out period is not a full temporal cross-validation.
- No fairness, uncertainty-calibration, or spatial-leakage audit exists until a
  real dataset is available.
- A model trained on one city/season should not be silently applied to another.
- Predictions must never be presented as official warnings or health advice.

## 13. Tests

The ML suite (10 tests) covers:

- missing-column detection;
- missing-file refusal;
- quality filtering, time features and low-valid-fraction removal;
- chronological split with no future leakage;
- too-few-rows refusal;
- out-of-range value rejection;
- prediction-frame target optionality and refusal to impute;
- reproducible artifact writing with manifest/metrics.

Tests use deterministic synthetic fixtures and assert pipeline behaviour, never a
model score.
