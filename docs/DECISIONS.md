# Architecture decisions

This file records decisions that shaped the platform, including the ones that
were forced by the development environment. Each entry states the context, the
decision, the consequences, and what would have to change for the decision to be
revisited.

Decisions are append-only. If a decision is superseded, add a new ADR rather
than rewriting history.

---

## ADR-001: Modular monolith, not microservices

**Status:** Accepted

**Context.** The platform spans weather ingestion, satellite processing,
community reporting, ML, and a web client. Splitting these into services would
add deployment, networking, and consistency costs before there is any evidence
that independent scaling is needed.

**Decision.** Build a single Django project with one app per bounded capability
(`weather`, `alerts`, `air_quality`, `environment`, `heat`, `incidents`,
`intelligence`, `climate`, `rainfall`, `locations`, `accounts`, `core`). Shared
provider adapters live in `data_pipelines/`. The ML pipeline is a separate Python
package (`ml/`) but runs as a batch job against the same database contract.

**Consequences.** One deployable API, one migration history, and simple
transactions across modules. Modules must communicate through service functions
and models, not by importing another app's views. A future split is possible at
app boundaries but is explicitly out of scope.

---

## ADR-002: Fixed, conventional stack

**Status:** Accepted

**Context.** The project needs a stack that is easy to hand over: a typed React
SPA, a Django/DRF API, PostGIS, and a standard Python data/ML toolchain.

**Decision.** Use React 18 + TypeScript + Vite + Tailwind + React Router + React
Leaflet + Recharts + Axios + TanStack Query on the client, and Django + DRF +
GeoDjango on the server, with PostgreSQL/PostGIS as the production database.
Python ML uses Pandas, NumPy, Scikit-learn, XGBoost, and Joblib. Deployment is
Docker Compose only; no Kubernetes.

**Consequences.** The stack is deliberately boring and well documented. New
dependencies should fit one of these roles rather than introduce a parallel
framework.

---

## ADR-003: Portable GeoJSON storage in development

**Status:** Accepted (environment constraint)

**Context.** Production targets PostgreSQL + PostGIS and GeoDjango. The Windows
development machine used to build this repository has no Docker daemon, no
PostgreSQL server, no PostGIS, and no GDAL/GEOS libraries. Requiring those just
to run tests would make the codebase unverifiable here.

**Decision.** Keep `DB_ENGINE=postgres` as the production path and ship a
PostGIS-enabled Compose stack. For local development, default to SQLite and
store geometry as validated GeoJSON (`JSONField`) on the models. Spatial
operations that matter to the product (point-in-polygon, distance, grid
generation, area measurement, reprojection) are implemented in
`apps/core/geometry.py` using Shapely and pyproj, with the same EPSG:4326 /
EPSG:32645 conventions as the production design. `source.boundary`,
`GridCell.geometry`, and incident points are all plain GeoJSON.

**Consequences.**

- The API contract and frontend are identical in both modes.
- Queries that would use PostGIS spatial indexes (for example, true
  point-in-polygon filtering in SQL) are done in Python or approximated with
  bounding boxes. This is acceptable for one city and a 250-cell grid.
- `django.contrib.gis` is not in `INSTALLED_APPS`; the `Area.boundary` field is
  a JSON field, not a `MultiPolygonField`.
- Do not claim native GeoDjango/PostGIS storage is active. The health endpoint
  reports `"spatial_engine": "shapely (portable GeoJSON mode)"` when SQLite is
  in use.
- Before production launch, migrate the geometry fields to PostGIS and add
  spatial indexes. The surrounding serializers and API shapes should not need
  to change.

---

## ADR-004: Provenance and data state are part of every environmental payload

**Status:** Accepted

**Context.** A civic tool that mixes forecasts, reanalysis, satellite
observations, official warnings, and resident reports must not present them as
interchangeable numbers. Users need to know what they are looking at.

**Decision.** Every environmental model carries a `DataSource` foreign key.
Every API response that returns environmental data includes a `state`
(`AVAILABLE`, `PARTIAL`, `STALE`, `UNAVAILABLE`, `PROCESSING`, `INVALID`),
a `source` summary (name, provider type, attribution, licence, resolution),
retrieval/observation timestamps, units, and a reason when data is missing.
Freshness is computed from the most recent successful retrieval, not from the
request time. Unavailable modules return an empty result plus an explicit
`reason`; they never return a placeholder value.

**Consequences.** Serializers and pages are more verbose, but the UI can render
honest provenance panels and data-state badges. Provider adapters must persist
raw retrieval metadata. Any new endpoint that returns environmental values must
follow the same envelope.

---

## ADR-005: Use OSM boundary and locality points, clearly labelled as community data

**Status:** Accepted

**Context.** No official KMC boundary or ward GeoJSON was available without a
licence or manual acquisition. OpenStreetMap has a maintained boundary relation
for Kolkata and a useful set of named places.

**Decision.** Bootstrap the city boundary from OSM relation 9381363
(`admin_level=8`, Wikidata Q1348, ODbL) and import OSM `place=*` points as
neighbourhoods. The measured area (about 200 km²) is stored with the source
reference. The API and UI call this "Kolkata Municipal Corporation" for
familiarity but attribute it to OpenStreetMap and state that it is not an
official KMC boundary. Locality points are **not** wards and are never described
as administrative units.

**Consequences.** The platform has usable geography on day one, with an honest
provenance trail. Replacing it with an official KMC/ward dataset is a data swap,
not an architecture change. Neighbourhood-level aggregation is point-based and
must not be presented as ward statistics.

---

## ADR-006: Deterministic 1 km analytical grid in EPSG:32645

**Status:** Accepted

**Context.** Satellite and model products have different native resolutions.
Comparing them requires a stable analysis unit that does not drift between runs.

**Decision.** Generate a deterministic grid of 1 km cells clipped to the city
boundary, using UTM zone 45N (EPSG:32645) for construction and EPSG:4326 for
API output. The version string (`KMC-1KM-V1`) and cell codes
(`KOLKATA-KMC-1KM-V1-R###-C###`) are stable. Each cell stores both the clipped
`geometry` and the unclipped `full_geometry`, plus `coverage_fraction` and
`area_km2` so downstream consumers can filter edge cells. The grid is
reproducible from the boundary and version parameters.

**Consequences.** Satellite ingestion, ML features, and map layers join on
`cell_code`. Changing cell size or extent requires a new grid version; never
mutate a published version in place.

---

## ADR-007: ML metrics are artifact-gated

**Status:** Accepted

**Context.** It is easy to train a model on a small or leaky dataset and publish
an impressive-looking score. That would violate the project's honesty contract.

**Decision.** The heat model has no hand-written metrics and no default
predictions. Training writes an artifact directory containing the model,
metrics, feature list, training manifest, and dataset hash. Registration refuses
artifacts that are missing a reproducible evaluation, use a random split, or
were trained on insufficient data (the pipeline requires at least 500 rows,
20 distinct dates, and 10 test dates). The API only reports model information
and predictions after a complete artifact is registered and a prediction run is
ingested. Until then, `/heat/predictions/` and `/heat/model-info/` return
`UNAVAILABLE` with a reason.

**Consequences.** The heat page is honest but empty in this environment. Any
future number shown on the page must be traceable to a registered artifact and
a prediction run. Synthetic test fixtures are used only inside the test suite.

---

## ADR-008: Community reports are moderated, not auto-merged

**Status:** Accepted

**Context.** Resident reports are valuable but unverified and can be duplicated,
mistaken, or malicious. Automatically merging reports would hide uncertainty.

**Decision.** Require authentication to submit. Store reporter identity but never
expose it publicly. New reports are `SUBMITTED` and publicly labelled
`UNVERIFIED`. Only moderators can move reports through `UNDER_REVIEW`,
`VERIFIED`, `RESOLVED`, `REJECTED`, `DUPLICATE`, or `EXPIRED`; every transition
is written to an audit history. Duplicate detection returns suggestions within
250 m and 6 hours but never merges automatically. Rejected, duplicate, and
expired reports are hidden from public lists. Images are type-checked, size
limited, re-encoded, and stripped of EXIF before storage. Owners may edit only
while their report is unverified or under review.

**Consequences.** The public feed is smaller but more trustworthy. Moderator
capacity is a product dependency. The audit trail supports later review and
abuse handling.

---

## ADR-009: Deterministic rules for insights, with visible evidence

**Status:** Accepted

**Context.** "AI recommendations" are hard to audit. For a civic tool, it is more
useful to show why an insight exists than to generate fluent text.

**Decision.** Insights are produced by a small, versioned rule engine
(`ruleset_version`). Each rule reads stored evidence (weather, rainfall,
alerts, air quality, satellite observations, community reports), applies an
explicit threshold, and returns a structured insight with severity, validity
window, and evidence items that each carry source and freshness. When a module
is unavailable, the rule is skipped and the response carries a data-availability
caveat rather than inventing a condition. Insights can be generated on read or
persisted by a moderator for history.

**Consequences.** Recommendations are reproducible and testable. The rule
engine is intentionally not a general LLM; adding probabilistic or learned
recommendations would require a separate, evaluated design.

---

## ADR-010: Token authentication with privacy-preserving public responses

**Status:** Accepted

**Context.** The product needs accounts for reporting and saved locations but
must not turn community reports into a directory of residents.

**Decision.** Use DRF token authentication for the SPA (with session auth kept
for the Django admin). Registration and login are throttled. Public incident
serializers omit reporter identity, email, and moderation notes; the history
endpoint exposes status changes but never moderator identities. Moderation
endpoints require an `is_moderator` flag on the user.

**Consequences.** Tokens are stored in browser storage by the SPA, which is
acceptable for this project but should be revisited if the threat model changes
(for example, move to httpOnly cookies with CSRF protection). Password reset and
email verification are not implemented; accounts are development-grade.

---

## ADR-011: No fabricated data in product databases

**Status:** Accepted

**Context.** Demo data makes screenshots look complete but destroys trust and
hides integration failures.

**Decision.** The product database is only populated by real provider calls or
by community submissions. There are no seed fixtures for weather, alerts, air
quality, satellite observations, climate metrics, or ML predictions. Tests use
deterministic synthetic fixtures in the test database only. When a provider is
not configured, the UI shows an unavailable state with the reason and the
missing credential.

**Consequences.** Some pages are empty in a fresh environment. That is the
correct behaviour. Screenshots and documentation must show honest states, not
invented numbers.

---

## ADR-012: Ingestion is explicit and batch-oriented

**Status:** Accepted

**Context.** Provider calls can be slow or rate-limited, and some (CPCB, IMD,
Earth Engine) require credentials. Doing ingestion inside user requests would
make the API fragile and hide failures.

**Decision.** Ingest with idempotent Django management commands
(`bootstrap_kolkata`, `fetch_weather`, `fetch_weather_history`,
`fetch_climate`, `fetch_alerts`, `fetch_cpcb`,
`ingest_landsat_observations`, `register_heat_model`,
`ingest_heat_predictions`). Requests read stored records through selectors and
compute derived views (rainfall summaries, insights) from them. Commands are
safe to re-run; they update or skip existing natural keys rather than
duplicating rows.

**Consequences.** Freshness depends on an external scheduler (Task Scheduler,
cron, or a Compose sidecar). The API can serve stale data honestly rather than
blocking. Operator documentation must include the cadence and failure modes
(see `OPERATIONS.md`).

---

## ADR-013: SPA served by Nginx in Docker, Vite in development

**Status:** Accepted

**Context.** The frontend is a client-side React application with API calls. It
needs a development server with hot reload and a production server that can
proxy API and media requests without CORS complexity.

**Decision.** Use Vite (`:5173`) with `/api` and `/media` proxies in development.
For production, build static assets in a Node stage and serve them from Nginx,
proxying `/api/`, `/media/`, and `/admin/` to the backend service. Compose maps
host `5173` to container port `80`. The API base URL is `/api/v1` at build time.

**Consequences.** One origin in production avoids CORS and cookie issues. The
Docker image must be rebuilt when the API base URL changes. The dev server and
production server have different routing behaviour, so smoke-test the built
image before relying on it.

---

## ADR-014: Synthetic fixtures for tests, bounded to a small Kolkata rectangle

**Status:** Accepted

**Context.** Tests that depend on live provider calls or the bootstrapped city
are slow, flaky, and non-deterministic. Tests that depend on a full 250-cell
grid are harder to reason about.

**Decision.** Backend tests use a synthetic rectangular area
(`88.34–88.38`, `22.54–22.58`) and a deterministic `TEST-1KM-V1` grid. Provider
adapters are tested against recorded payload shapes and normalizers, not live
endpoints. ML tests generate small labelled datasets and assert the pipeline's
gates and determinism. Frontend tests cover formatting and shared components,
not pixel-level layout.

**Consequences.** Tests run offline and in seconds. They do not prove that live
provider contracts still match; that is covered by the documented manual probe
and by running the ingestion commands against a real environment.

---

## Revisit triggers

| Decision | Revisit when |
| --- | --- |
| ADR-003 | A machine with Docker/PostGIS is the standard dev environment, or spatial query volume grows beyond one city |
| ADR-005 | An official KMC boundary/ward dataset is licensed for use |
| ADR-007 | A real Landsat/GEE export and labelled dataset are available |
| ADR-008 | Moderation volume requires assignment, SLAs, or trusted-reporter tiers |
| ADR-010 | The product handles sensitive personal data or public launch security review |
| ADR-012 | Ingestion needs sub-hourly cadence, retries, or provider webhooks |
