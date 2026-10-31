# Architecture

## 1. Shape of the system

Aaboh is a **modular monolith**: one Django project, one database, one
React single-page application. Modules have explicit boundaries (Django apps and
frontend feature folders) but run in the same process. There are no
microservices, message brokers, Kubernetes manifests, or cross-service network
calls.

```
Browser
  │
  ├── React SPA (Vite dev server or Nginx)
  │      TanStack Query → Axios → /api/v1
  │
  └── Django + DRF ── SQLite/PostGIS
          │
          ├── Open-Meteo / ERA5-Land archive   (implemented, live)
          ├── IMD                              (adapter implemented, credential blocked)
          ├── CPCB / data.gov.in               (adapter implemented, credential blocked)
          ├── Google Earth Engine / Landsat    (export + ingestion implemented, credential blocked)
          └── Community reports                (implemented)
```

Ingestion is performed by explicit management commands rather than background
workers. This keeps every write auditable and makes the current manual cadence
honest; a scheduler can invoke the same commands later without changing the data
model. Every attempt writes an `IngestionRun` row.

## 2. Backend apps

| App | Responsibility | Key models |
| --- | --- | --- |
| `core` | Provenance, data states, health/readiness, API root, shared geometry, error envelope, pagination | `DataSource`, `IngestionRun` |
| `accounts` | Custom user, roles, preferences, saved private locations, token auth | `User`, `UserPreference`, `SavedLocation` |
| `locations` | Areas, OSM localities, versioned deterministic grid | `Area`, `Neighbourhood`, `GridDefinition`, `GridCell` |
| `weather` | Open-Meteo current/hourly/daily/archive ingestion and selection | `WeatherLocation`, `WeatherRecord` |
| `alerts` | IMD official warnings and alert geometry | `OfficialAlert` |
| `air_quality` | CPCB stations and station measurements | `AQIStation`, `AQIMeasurement` |
| `environment` | Landsat scenes and per-cell satellite indices | `SatelliteScene`, `EnvironmentalObservation` |
| `heat` | Model registry, prediction runs, cell predictions, descriptive hotspots | `ModelVersion`, `PredictionRun`, `CellPrediction` |
| `rainfall` | Read-only derivation from weather records | none |
| `climate` | ERA5-Land baselines, annual/seasonal metrics, trends | `ClimateBaseline`, `ClimateMetric` |
| `incidents` | Community submissions, sanitised images, moderation history | `IncidentReport`, `IncidentAttachment`, `IncidentStatusHistory` |
| `intelligence` | Deterministic rules, evidence, optional persisted briefings | `Recommendation`, `RecommendationEvidence` |

`rainfall` intentionally has no tables: it aggregates the same stored
Open-Meteo/ERA5-Land weather records used by the weather module. This avoids a
second copy of the same physical quantity.

## 3. Provenance and quality model

Provenance and freshness are separate concepts:

- **Provenance** answers *where did this come from and under what licence?*
  (`DataSource`).
- **Quality state** answers *can I use this right now?* (`DataState`).
- **Ingestion audit** answers *what did the last acquisition attempt do?*
  (`IngestionRun`).

`apps.core.quality` implements:

| State | Meaning |
| --- | --- |
| `AVAILABLE` | A recent record exists from the documented source |
| `PARTIAL` | Some records/fields exist, coverage is incomplete |
| `STALE` | Latest success is outside the source's expected refresh window |
| `UNAVAILABLE` | No verified data; nothing has been estimated to fill the gap |
| `PROCESSING` | An ingestion run is currently running |
| `INVALID` | Record failed temporal/quality validation (e.g. future timestamp) |

`source_availability()` derives the state from the latest `IngestionRun` and the
source's `expected_refresh_minutes`. Weather endpoints additionally apply a
3-hour freshness window to current/forecast records.

Every environmental response carries a source summary, timestamps, units and,
where relevant, a `reason` for unavailability. This is a product requirement,
not just documentation.

## 4. Geography and spatial strategy

### Development (current)

- SQLite database.
- `apps.core.fields.GeometryField` stores validated GeoJSON in a JSON/text
  column.
- Shapely and pyproj provide point-in-polygon, centroid, intersection, geodesic
  area, and distance calculations.
- External GeoJSON is EPSG:4326.
- The analytical grid is generated in **EPSG:32645 (UTM zone 45N)** at 1,000 m
  and converted back to EPSG:4326 for API delivery.

### Production target

- PostgreSQL 16 + PostGIS 3.4, provisioned in `docker-compose.yml`.
- `infra/postgres/init.sql` enables `postgis` and `postgis_topology`.
- The portable field is intentionally isolated so it can be replaced by native
  `django.contrib.gis.db.models` geometry without changing API contracts.
- Native GeoDjango is not enabled because GDAL/GEOS were unavailable in the
  development environment. See `DECISIONS.md` ADR-003.

### Kolkata bootstrap

`bootstrap_kolkata` imports:

1. OSM relation 9381363 (`admin_level=8`, Wikidata Q1348) as the city area.
2. 124 named OSM locality **points** as neighbourhoods — not official wards.
3. A deterministic 250-cell 1 km grid (`TEST-1KM-V1` in tests; production
   version is generated from the area boundary).

The measured area is 200.00 km². The boundary is community-maintained and is
labelled as such in API metadata and UI.

## 5. Backend request conventions

- All public endpoints live under `/api/v1/`.
- OpenAPI: `/api/schema/`, Swagger `/api/docs/`, ReDoc `/api/redoc/`.
- Authentication: DRF token (`Authorization: Token <key>`) plus session auth.
- Default permission: `IsAuthenticatedOrReadOnly`.
- Pagination: 50 items per page (`count`/`next`/`previous`/`results`) on generic
  list endpoints. Bespoke map/list endpoints return their own envelopes.
- Filtering: `django-filter` + explicit query parameter validation in views.
- Errors use a consistent envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Invalid input.",
    "details": {"field": ["Explanation"]}
  }
}
```

- Throttles: anonymous 120/min, authenticated 600/min, auth 10/min, incident
  creation 12/hour.
- Uploads: maximum 4 images, 5 MB each after validation, JPEG/PNG/WebP only,
  minimum 200×200, maximum 6000×6000 and 24 MP, EXIF stripped, re-encoded as
  JPEG, SHA-256 stored.

## 6. Domain boundaries and honesty rules

1. **Official warnings are never inferred.** Only IMD-sourced rows appear in
   `/alerts/`; the absence of rows is presented as unavailable or empty, never
   as “safe”.
2. **Forecasts are not observations.** Open-Meteo current conditions are labelled
   provider forecast/analysis output, not station measurements.
3. **Station AQI is not a surface.** CPCB values remain station-specific; the
   platform does not interpolate a neighbourhood AQI map.
4. **LST is not air temperature.** Landsat-derived and ML-predicted values are
   labelled land-surface temperature and are never framed as heat warnings.
5. **Community reports are unverified by default.** Public serializers expose an
   `UNVERIFIED`/`VERIFIED` state; reporter identity/email is never public.
6. **No synthetic production data.** The `development_fixture` source exists
   only for automated tests. Ingestion commands write only provider data.
7. **ML metrics are artifact-driven.** A model is registered with metrics only
   from a completed evaluation artifact; predictions require a scored model.
8. **Insights are deterministic and evidence-linked.** Each rule returns source,
   timestamp, units, quality and caveats; a rule does not fire without its input.

## 7. Frontend architecture

```
src/
  api/            axios client, typed contracts, TanStack Query hooks
  auth/           AuthProvider + context/hooks
  components/
    layout/       header, footer, app shell
    map/          CivicMap, boundary/grid layers, pickers, incident map
    ui/           PageHeader, DataState, SourcePanel, StatCard, Feedback…
    insights/     InsightCard with evidence/caveats
  pages/          one route per product area
  lib/            formatting, labels, constants
  test/           Vitest setup and unit tests
```

- `App.tsx` defines the route table.
- The Vite dev server proxies `/api` and `/media` to `127.0.0.1:8000`.
- The production image serves static assets through Nginx and proxies the same
  paths to Django.
- React Query owns server state and caching; there is no global store.
- Auth is token-based, persisted in `localStorage`, revalidated against
  `/users/me/` on load, and cleared on 401/logout.
- All maps use OpenStreetMap tiles with visible attribution and a Kolkata
  centre; no proprietary basemap is used.
- Every data page renders an explicit `DataStateNotice` and `SourcePanel`
  instead of blank charts when a layer is unavailable.

## 8. Deployment topology

Docker Compose (`docker-compose.yml`):

- `db`: `postgis/postgis:16-3.4`, persistent volume, PostGIS init SQL, healthcheck.
- `backend`: Django image, Postgres settings, migrations + bootstrap + runserver
  for the development stack, bind-mounted source, media volume, port 8000.
- `frontend`: multi-stage Node build → Nginx, port 5173:80, proxies API/media.

For a real production deployment, replace `runserver` with Gunicorn (already in
`backend/requirements/prod.txt`), terminate TLS at a reverse proxy, set
`DJANGO_DEBUG=false`, use a strong secret, restrict hosts/CORS, run `collectstatic`
with WhiteNoise (installed) or serve static files separately, and schedule
ingestion commands. See `OPERATIONS.md`.

## 9. Extension points

- Add a city by creating an `Area` + grid and running the same ingestion
  selectors; most endpoints already accept `?area=`.
- Add a provider by implementing an adapter under `data_pipelines/providers/`,
  a normaliser, and an ingestion service that records `IngestionRun`.
- Add native PostGIS by swapping the field and writing a data migration; API
  GeoJSON contracts stay unchanged.
- Add a rule by extending `apps/intelligence/services.py`; rules must accept
  unavailable inputs without firing and must attach evidence.
- Add a model task by extending `ModelTask`, training gates, and the artifact
  registry; metrics must come from a real evaluation file.
