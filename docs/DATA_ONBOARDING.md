# Real Data Onboarding and Model Training

This is the operator runbook for moving the platform from its current honest
"blocked" states to real provider data and a trained heat model. It is written
for the credentials and data that do **not** exist in this repository yet.

The rule for every step is the same: configure one provider, run one ingestion,
verify the API response and its provenance, and only then expose the result in
the product. Never fill a gap with sample values, and never present a fallback
as an observation, forecast, or official warning.

**Current baseline:** Open-Meteo weather, ERA5-Land history, climate metrics,
Kolkata geography, the 1 km grid, community reports, and deterministic insights
already work. IMD alerts, CPCB air quality, Landsat/GEE layers, and ML artifacts
are implemented but blocked on credentials or a real dataset.

---

## 0. Before requesting any credential

1. Copy `.env.example` to `.env` and keep `.env` untracked. It is already in
   `.gitignore`.
2. Confirm the baseline is healthy:

   ```powershell
   cd backend
   .venv\Scripts\python.exe manage.py check
   .venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
   ```

3. Open these endpoints and confirm each reports its real state:

   - `http://127.0.0.1:8000/api/v1/health/`
   - `http://127.0.0.1:8000/api/v1/system/config/`
   - `http://127.0.0.1:8000/api/v1/system/data-status/`

4. Restart Django after changing `.env`. Settings are read at process start.

5. Keep credentials scoped to one machine or one service account. Do not put
   them in source, screenshots, issue reports, or frontend build variables.

---

## 1. Credential matrix

| Provider | What to request | Environment variables | First command | Success signal |
| --- | --- | --- | --- | --- |
| IMD | API access and the current warning endpoint contract | `IMD_API_KEY`, `IMD_API_KEY_HEADER`, optional `IMD_BASE_URL` | `fetch_alerts` | `/api/v1/alerts/` reports `AVAILABLE` and official records |
| CPCB / data.gov.in | API key for the CPCB resource | `CPCB_API_KEY`, optional `CPCB_RESOURCE_ID` | `fetch_cpcb --max-pages 2` | Stations and measurements appear with station timestamps |
| Google Earth Engine | A Google Cloud project with Earth Engine enabled, a service account, and a grid table asset | `GEE_PROJECT_ID`, `GEE_SERVICE_ACCOUNT_EMAIL`, `GEE_SERVICE_ACCOUNT_KEY_FILE` | `python -m src.heat.gee_landsat_export ...` | A CSV in the Drive folder `climatesense` |
| Open-Meteo | No key for the public endpoint | `OPEN_METEO_ENABLED` | `fetch_weather`, `fetch_weather_history`, `fetch_climate` | Already working; this is the reference for a healthy module |

Do not claim that a provider is integrated until its command has run against
the live service and the API has returned the expected provenance and units.

---

## 2. IMD official warnings

### What to obtain

Request API access from IMD and confirm, in writing if possible:

- the base URL and endpoint path for district warnings;
- the authentication header name and whether the key is sent as a header or a
  query parameter;
- the district identifier for Kolkata;
- rate limits, update cadence, and whether redistribution/display is permitted.

The adapter currently defaults to:

```text
base URL: https://api.imd.gov.in/api/v1
endpoint: districtwarning
header:   X-API-Key
```

These defaults are **not confirmed** against a working account. They are
configurable because the public probe only returned
`{"error":"API key missing"}`.

### Configure and ingest

```dotenv
IMD_API_KEY="..."
IMD_API_KEY_HEADER="X-API-Key"
IMD_BASE_URL="https://api.imd.gov.in/api/v1"
```

```powershell
cd backend
.venv\Scripts\python.exe manage.py fetch_alerts
# or, when the district id is known:
.venv\Scripts\python.exe manage.py fetch_alerts --district-id <id>
```

Then verify:

- `GET /api/v1/alerts/` returns `data_state: "AVAILABLE"`;
- each record has the IMD source, `issued_at`, hazard, severity, and a source
  URL;
- expired warnings are no longer shown as current;
- an empty feed shows an honest empty state, not an invented alert.

### If the live payload differs

Capture a sanitized payload (remove the key and any personal data), add it as a
test fixture, update `data_pipelines/providers/imd.py`, and add a regression
test. Do not adjust the normaliser from memory.

---

## 3. CPCB station air quality

### What to obtain

1. Create/log in to a [data.gov.in](https://data.gov.in/) account.
2. Generate an API key from the account profile.
3. Confirm the CPCB resource id. The template currently uses
   `3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69`.
4. Confirm the field names, pollutant units, averaging period, and update
   cadence against the live resource.

### Configure and ingest

```dotenv
CPCB_API_KEY="..."
CPCB_RESOURCE_ID="3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
CPCB_BASE_URL="https://api.data.gov.in/resource"
```

```powershell
cd backend
.venv\Scripts\python.exe manage.py fetch_cpcb --max-pages 2
```

Start with two pages. A large first run against an unverified schema is harder
to diagnose than a small one.

Then verify:

- `GET /api/v1/air-quality/stations/` lists only stations with real
  coordinates;
- each measurement keeps its station, timestamp, pollutant unit, and CPCB
  provenance;
- AQI is only shown when the provider supplies it; no AQI is interpolated for
  neighbourhoods;
- stale measurements are labelled stale.

If the resource returns no Kolkata stations, keep the unavailable/empty state
and record the provider limitation. Do not create a station.

---

## 4. Landsat and Google Earth Engine

This step produces the real dataset used by both the heat layers and the ML
pipeline. It has three parts: credentials, grid asset, export.

### 4.1 Credentials

1. Create a Google Cloud project and enable the Earth Engine API.
2. Register the project for Earth Engine access.
3. Create a service account.
4. Grant it the minimum roles needed to read Landsat and run batch exports.
5. Download a JSON key and store it outside the repository, for example:

   ```dotenv
   GEE_PROJECT_ID="your-ee-project"
   GEE_SERVICE_ACCOUNT_EMAIL="climate-export@your-ee-project.iam.gserviceaccount.com"
   GEE_SERVICE_ACCOUNT_KEY_FILE="C:\secure\climatesense-ee-key.json"
   ```

6. Install the export dependencies into the backend virtual environment:

   ```powershell
   backend\.venv\Scripts\python.exe -m pip install -r ml\requirements.txt
   ```

Never commit the JSON key. The `.gitignore` already blocks
`service-account*.json`, `*.pem`, and `*.key`.

### 4.2 Build the grid asset

The export expects an Earth Engine `FeatureCollection` with a `cell_code`
property. Export the generated Django grid:

```powershell
cd backend
.venv\Scripts\python.exe manage.py export_grid_geojson `
  --area kolkata `
  --output ..\ml\data\raw\kolkata_grid_1km_v1.geojson
```

Upload that GeoJSON to Earth Engine as a table asset, for example:

```text
projects/your-ee-project/assets/kolkata_grid_1km_v1
```

The grid is an analytical aggregation unit clipped to the OSM boundary. It is
not an official ward map.

### 4.3 Export observations

From the `ml/` directory:

```powershell
cd ml
..\backend\.venv\Scripts\python.exe -m src.heat.gee_landsat_export `
  --grid-asset projects/your-ee-project/assets/kolkata_grid_1km_v1 `
  --start 2013-01-01 --end 2026-01-01 `
  --output data\raw\kolkata_lst_2013_2026.csv `
  --wait
```

Notes:

- Landsat 8 starts in 2013; Landsat 9 starts in 2021. The pipeline merges both.
- A longer date range gives the model more seasons and years, but cloud cover
  and the 16-day revisit limit usable observations.
- The export writes to the Google Drive folder `climatesense`. Download the CSV
  to the `--output` path before training.
- If the command exits for missing credentials or a missing/empty grid asset,
  nothing is written. That is intentional.

### 4.4 Ingest into Django

```powershell
cd backend
.venv\Scripts\python.exe manage.py ingest_landsat_observations `
  --dataset ..\ml\data\raw\kolkata_lst_2013_2026.csv
```

Then verify `/api/v1/environment/layers/` and the heat observation endpoints
show real scene dates, grid cells, and provenance. Rows with
`valid_pixel_fraction < 0.5` are dropped by default.

---

## 5. Model training: a defensible accuracy plan

"Best possible accuracy" is not a number to promise in advance. It is the
result of enough representative data, leakage-free validation, and honest
reporting. The pipeline currently enforces the first part of that discipline;
the rest is the operator's job.

### 5.1 Data requirements

- Use multiple years, not one dry season. Landsat 8 plus 9 from 2013 onward is
  the practical range.
- Keep all seasons represented in both training and test periods.
- Retain only rows that pass the quality gates: valid pixel fraction at least
  `0.5`, plausible LST/indices, valid coordinates.
- Record the exact export date range, scene ids, cloud thresholds, grid version,
  and dataset hash in the artifact manifest.
- Do not mix synthetic test fixtures into a training dataset.

The current training gates are intentionally strict: at least 500 rows, 20
distinct observation dates, and 10 held-out dates. More data is better, but
coverage across seasons and years matters more than raw row count.

### 5.2 Split strategy and leakage

The existing split is chronological: the latest 20% of dates are held out.
That prevents future observations leaking into training, but adjacent 1 km cells
from the same Landsat scene are spatially correlated.

For a stronger evaluation, add and report a second hold-out:

- hold out whole scenes, or
- hold out spatial blocks of cells, or
- hold out one or more years entirely.

Keep the untouched test period for final reporting. Tune only on a validation
window inside the training period.

### 5.3 Train and evaluate

```powershell
cd ml
..\backend\.venv\Scripts\python.exe -m src.heat.train `
  --dataset data\raw\kolkata_lst_2013_2026.csv
```

The run writes `model.joblib`, `metrics.json`, and `manifest.json` under
`ml/artifacts/heat/<run-id>/`. The command refuses to overwrite an existing
run, which keeps runs reproducible.

Re-evaluate a saved artifact without changing its stored metrics:

```powershell
..\backend\.venv\Scripts\python.exe -m src.heat.evaluate `
  --artifact artifacts\heat\<run-id> `
  --dataset data\raw\kolkata_lst_2013_2026.csv `
  --output artifacts\heat\<run-id>\evaluation.json
```

Report, at minimum:

- MAE and RMSE in degrees Celsius;
- R2 and mean signed error;
- row and date counts in train and test;
- the exact test date range;
- per-season error, if sample size allows;
- a naive baseline (for example, predicting the training-period mean or a
  seasonal climatology) so the model's value is visible.

A single aggregate R2 is not enough to justify an operational claim.

### 5.4 Tune only after the baseline is honest

Once a reproducible baseline exists:

1. Add physically motivated features only if they are available at prediction
   time and have documented provenance.
2. Tune a small, explicit hyperparameter grid on a validation period.
3. Compare against the baseline with the same split.
4. Keep the simplest model that wins by a meaningful margin.
5. Re-run a final evaluation on the untouched test period.
6. Write down the limitations: LST is not air temperature, Landsat revisits are
   sparse, cloud cover biases coverage, and metrics describe the evaluation
   period only.

Do not select a model because it has the best single number. Check bias,
seasonal behavior, and failure cases.

### 5.5 Register and serve

Review the metrics and manifest first:

```powershell
cd backend
.venv\Scripts\python.exe manage.py register_heat_model `
  --artifact ..\ml\artifacts\heat\<run-id>
```

The model registers as non-operational. Add `--operational --activate` only
after review. Then generate predictions and ingest them:

```powershell
cd ml
..\backend\.venv\Scripts\python.exe -m src.heat.predict `
  --artifact artifacts\heat\<run-id> `
  --dataset data\raw\kolkata_features.csv `
  --output data\raw\kolkata_predictions.csv
```

```powershell
cd backend
.venv\Scripts\python.exe manage.py ingest_heat_predictions `
  --predictions ..\ml\data\raw\kolkata_predictions.csv
```

The product must keep the model version, run date, validation period, and
limitations visible alongside any prediction.

---

## 6. Verification checklist after each provider

- [ ] The ingestion command exits successfully and reports written/skipped rows.
- [ ] The relevant `/system/data-status/` module is `AVAILABLE`, not manually
      forced.
- [ ] The API response includes source, retrieved time, units, and quality.
- [ ] An empty provider response still produces an honest empty state.
- [ ] Stale data is labelled `STALE`.
- [ ] No fixture or sample data entered the development database.
- [ ] A provider failure does not break unrelated modules.
- [ ] The new payload shape has a regression test if it differs from the
      unverified assumed shape.
- [ ] `.env`, key files, and raw personal data are not staged for commit.

## 7. What to send when asking for the next integration step

Provide only what is needed and never paste a secret into chat:

- which provider you are working on;
- whether the credential is configured (yes/no), not the credential itself;
- the exact command and the sanitized error or success output;
- for a schema mismatch, a sanitized sample response with the key removed;
- for ML, the dataset row/date counts, date range, and the generated
  `metrics.json` and `manifest.json`.

With that, the next step can be a code change, a normaliser fix, a test fixture,
or a training/evaluation run. No claim will be upgraded until the live path has
been verified.
