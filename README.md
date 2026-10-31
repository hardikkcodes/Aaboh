# Aaboh Platform

Hyperlocal environmental intelligence for Kolkata, built as a production-minded
modular monolith. The platform separates **observations**, **forecasts**,
**predictions**, **official warnings**, **community reports**, and **derived
insights** so that a user can always see what kind of evidence they are looking
at, where it came from, and how fresh it is.

The repository currently runs end-to-end on a Windows development machine
without Docker, PostgreSQL, or GDAL. Production provisioning for PostgreSQL +
PostGIS is included, but native GeoDjango storage is not active yet (see
[ADR-003](docs/DECISIONS.md#adr-003-portable-geojson-storage-in-development)).

---

## Status at a glance

| Capability | Status | What is actually true today |
| --- | --- | --- |
| Accounts | **Working** | Sign up, login, password reset, email confirmation, password change, account deletion. Set `EMAIL_HOST` to send real email |
| Waterlogging terrain | **Working for Kolkata** | Copernicus elevation per cell on the Rainfall page. Training is ready but waits for 300 real reports |
| Bangla | **Working** | Translates the page and server text. Reports and official alert wording stay as written |
| Place search and routes | **Needs a key for Google** | Set `GOOGLE_MAPS_API_KEY` and enable Places API (New) and Routes API. Without it, search uses local places and routes are drawn by hand |
| Regional coverage | **Working** | North and South Kolkata (split at latitude 22.55, approximate), North and South 24 Parganas |
| Kolkata geography | **Working** | OSM relation 9381363 boundary, 124 OSM locality points, 250-cell deterministic 1 km grid in EPSG:32645 |
| Weather forecast/current | **Working** | Live Open-Meteo ingestion; explicitly model output, not station observations |
| Weather history / rainfall | **Working** | ERA5-Land daily archive via Open-Meteo, ~9 km reanalysis |
| Climate metrics/trends | **Working** | Live ERA5-Land annual/seasonal metrics with 1991–2020 baseline |
| Official alerts | **Working** | SACHET feed, matched by named place or by state (`ALERT_STATE_TERMS`). The IMD adapter is unused without `IMD_API_KEY` |
| Air quality | **Blocked on credential** | CPCB/data.gov.in adapter implemented; no `CPCB_API_KEY`, so no stations or AQI are shown |
| Satellite heat/environment | **Working for Kolkata** | Landsat from Microsoft Planetary Computer, no account needed. Run `ml/src/heat/pc_landsat_export.py`, then ingest. The data file is not in git |
| Heat ML predictions | **Tested, not in use** | Surface-heat model: 1.54 °C error against 3.08 °C for a cell-and-month average. It needs same-day satellite inputs, so no predictions are served |
| Community reports | **Working** | Authenticated submissions, image sanitisation, duplicate hints, moderator workflow, audit history |
| Area-first place status | **Working** | `/place/<area>` and neighbourhood pages aggregate weather, rain, a rule-based waterlogging signal, heat, air quality, alerts, and nearby reports with explicit states |
| Insights | **Working** | Deterministic rules over stored evidence, with explicit data-availability caveats |
| PostGIS / GeoDjango | **Not active** | Docker Compose + PostGIS service provided; development uses SQLite and a portable GeoJSON field |

Nothing in the product fabricates an environmental value, station record,
official warning, model score, or partnership. Missing inputs produce an
explicit unavailable/partial state.

---

## Stack

- **Frontend:** React 18, TypeScript, Vite 6, Tailwind CSS 3, React Router 7,
  React Leaflet 4, Recharts 2, Axios, TanStack Query 5.
- **Backend:** Django 6, Django REST Framework 3.17, drf-spectacular,
  token + session authentication.
- **Data/spatial:** PostgreSQL/PostGIS as the production target; SQLite +
  Shapely/pyproj portable GeoJSON mode for local development.
- **ML:** Python, Pandas, NumPy, Scikit-learn, XGBoost, Joblib; GeoPandas /
  Earth Engine / Rasterio are optional export-side dependencies.
- **Deployment:** Docker Compose with PostGIS, Django, and an Nginx-served
  frontend.

---

## Quick start (Windows, no Docker)

Prerequisites: Python 3.12+ (developed on 3.14), Node 20+ (developed on 26),
Git. Use `npm.cmd` in PowerShell if script execution policy blocks `npm.ps1`.

```powershell
# 1. Environment
Copy-Item .env.example .env

# 2. Backend
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements\dev.txt
backend\.venv\Scripts\python.exe backend\manage.py migrate
backend\.venv\Scripts\python.exe backend\manage.py bootstrap_kolkata
backend\.venv\Scripts\python.exe backend\manage.py fetch_weather --area kolkata
backend\.venv\Scripts\python.exe backend\manage.py fetch_climate --area kolkata

# 3. Frontend
cd frontend
npm.cmd install
cd ..

# 4. Run (two terminals)
backend\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
cd frontend; npm.cmd run dev
```

Open <http://localhost:5173>. API docs are at
<http://127.0.0.1:8000/api/docs/> and the OpenAPI schema is
<http://127.0.0.1:8000/api/schema/>.

If `manage.py` is run from `backend/`, use `.venv\Scripts\python.exe manage.py`
instead. Both layouts are supported; the repository root is added to
`sys.path` by the Django settings.

### Docker Compose

```powershell
Copy-Item .env.example .env
docker compose up --build
```

- Frontend: <http://localhost:5173>
- Backend/API: <http://localhost:8000/api/v1/>
- PostGIS: `localhost:5432`

Docker Compose sets `DB_ENGINE=postgres` and runs migrations plus the Kolkata
bootstrap on start. The frontend image builds the SPA and serves it through
Nginx, proxying `/api/`, `/media/`, and `/admin/` to Django.

---

## Common commands

| Task | Command |
| --- | --- |
| Backend tests (73) | `cd backend; .venv\Scripts\python.exe -m pytest -q` |
| ML tests (10) | `cd ml; ..\backend\.venv\Scripts\python.exe -m pytest tests -q` |
| Frontend tests (10) | `cd frontend; npm.cmd test` |
| Type check | `cd frontend; npm.cmd run typecheck` |
| Lint | `cd backend; .venv\Scripts\python.exe -m ruff check .` and `cd frontend; npm.cmd run lint` |
| Django checks | `cd backend; .venv\Scripts\python.exe manage.py check` |
| OpenAPI validation | `cd backend; .venv\Scripts\python.exe manage.py spectacular --file ..\schema.yaml --validate` |
| Export grid for Earth Engine | `cd backend; .venv\Scripts\python.exe manage.py export_grid_geojson --area kolkata --output ..\ml\data\raw\kolkata_grid.geojson` |
| Frontend build | `cd frontend; npm.cmd run build` |

The `Makefile` wraps the same workflows (`make test`, `make lint`,
`make bootstrap`, `make weather`, `make climate`) on Unix-like shells.

### Ingestion commands

```powershell
cd backend
.venv\Scripts\python.exe manage.py bootstrap_kolkata [--skip-grid] [--skip-localities]
.venv\Scripts\python.exe manage.py fetch_weather --area kolkata --forecast-days 7
.venv\Scripts\python.exe manage.py fetch_weather_history --area kolkata --days 730
.venv\Scripts\python.exe manage.py fetch_climate --area kolkata --start-year 1991
.venv\Scripts\python.exe manage.py fetch_alerts                 # needs IMD_API_KEY
.venv\Scripts\python.exe manage.py fetch_cpcb                   # needs CPCB_API_KEY
.venv\Scripts\python.exe manage.py ingest_landsat_observations --dataset path\to\export.csv
.venv\Scripts\python.exe manage.py register_heat_model --artifact path\to\artifact
.venv\Scripts\python.exe manage.py ingest_heat_predictions --predictions path\to\predictions.csv
```

---

## Repository map

```
backend/
  apps/core/           provenance, quality states, health, API root, shared geometry
  apps/accounts/       custom user, preferences, saved locations, auth
  apps/locations/      areas, OSM localities, deterministic 1 km grid
  apps/weather/        Open-Meteo current/forecast/archive ingestion and selectors
  apps/alerts/         IMD official-warning adapter and storage
  apps/air_quality/    CPCB station adapter and station measurements
  apps/environment/    Landsat scene/observation ingestion and layers
  apps/heat/           model registry, prediction runs, hotspots, ML artifact ingestion
  apps/rainfall/       rainfall forecast/history derived from weather records
  apps/climate/        ERA5-Land metrics, baselines, linear trends
  apps/incidents/      community reports, uploads, moderation, duplicate hints
  apps/intelligence/   deterministic evidence-backed insight rules
  config/              Django settings, root URLs, WSGI/ASGI
  tests/               backend test suite
data_pipelines/
  providers/           Open-Meteo, IMD, CPCB HTTP adapters
  normalization/       provider payload normalisation
frontend/
  src/api/             typed API client, query hooks, domain contracts
  src/auth/            auth provider, context and hooks
  src/components/      layout, maps, UI primitives, insight cards
  src/pages/           all product routes
  src/lib/             formatting and display constants
  src/test/            Vitest setup and tests
ml/
  src/heat/            GEE export, features, training, evaluation, prediction
  tests/               deterministic pipeline tests
docs/                  architecture, API, data sources, ML, operations, decisions
infra/postgres/        PostGIS bootstrap SQL
```

---

## Data honesty contract

Every environmental payload is expected to carry:

- a **data state** (`AVAILABLE`, `PARTIAL`, `STALE`, `UNAVAILABLE`,
  `PROCESSING`, `INVALID`);
- **source** identity (name, provider type, attribution, licence, resolution);
- **observed/retrieved timestamps** in UTC;
- **units** and a dataset label;
- a **reason** and no substitute values when the layer is unavailable.

The frontend renders these states as badges and provenance panels. The backend
never fills missing provider data with synthetic values outside automated tests.
`schema.yaml` is generated from the running code; it is the authoritative
endpoint contract.

---

## Credentials and blockers

Copy `.env.example` to `.env`; never commit `.env`.

| Variable | Needed for | Current state |
| --- | --- | --- |
| `IMD_API_KEY` (+ `IMD_API_KEY_HEADER`) | Official IMD warnings | Not set; header name must be confirmed with IMD |
| `CPCB_API_KEY` | CPCB station air quality | Not set; `api.data.gov.in` timed out during probing |
| `GEE_PROJECT_ID`, `GEE_SERVICE_ACCOUNT_EMAIL`, `GEE_SERVICE_ACCOUNT_KEY_FILE` | Landsat/GEE export | Not set; no grid asset exists in Earth Engine |
| `CDS_API_KEY` | Optional direct Copernicus access | Not used; ERA5-Land is accessed through Open-Meteo |
| `DJANGO_SECRET_KEY`, database credentials | Production | Development defaults only |

See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md) for provider-by-provider
licences, resolutions, and caveats, and
[docs/DATA_ONBOARDING.md](docs/DATA_ONBOARDING.md) for the step-by-step
credential, ingestion, and ML training runbook.

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Development roadmap](docs/DEVELOPMENT_ROADMAP.md)
- [Data sources and provenance](docs/DATA_SOURCES.md)
- [Real data onboarding and ML training](docs/DATA_ONBOARDING.md)
- [API guide](docs/API.md)
- [ML methodology](docs/ML_METHODOLOGY.md)
- [Operations runbook](docs/OPERATIONS.md)
- [Testing strategy](docs/TESTING.md)
- [Architecture decisions](docs/DECISIONS.md)
- [Limitations and honest gaps](docs/LIMITATIONS.md)
- [ML package README](ml/README.md)

---

## Licence and attribution

Application code in this repository is provided for the project. Environmental
data remains subject to each provider's licence:

- OpenStreetMap data © OpenStreetMap contributors, ODbL 1.0.
- Weather data by Open-Meteo.com, CC BY 4.0.
- ERA5-Land / Copernicus Climate Change Service.
- USGS/NASA Landsat, public domain.
- IMD and CPCB/data.gov.in under their respective Government of India terms.

Map tiles are loaded from OpenStreetMap with visible attribution. The OSM
boundary is community-maintained and is **not** an official Kolkata Municipal
Corporation boundary.

## Disclaimer

This is decision support, not an official warning service or medical advice.
Always follow instructions from IMD, KMC, and emergency services. Absence of a
warning or report does not mean conditions are safe.
