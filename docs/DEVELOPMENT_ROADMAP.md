# Development roadmap

This roadmap is a status tracker, not a promise. A milestone is only marked
**Done** when the capability is implemented, documented, tested with
deterministic tests, and verified against the running stack. Provider-dependent
milestones stay **Blocked** until real credentials and data exist; the code
behind them may already be implemented.

**Last updated:** 2026-10-31

## Status legend

| Status | Meaning |
| --- | --- |
| **Done** | Implemented, tested, and usable in the current environment |
| **Partial** | Core path works; named gaps remain |
| **Blocked** | Code exists, but the milestone cannot be verified without an external input (credential, dataset, licence, or infrastructure) |
| **Not started** | No implementation yet |

---

## Milestone 0 — Foundation and guardrails

**Status: Done**

- Django 6 + DRF project with environment-driven settings.
- Custom user model, token + session authentication, moderator role.
- Shared `DataSource` provenance model, data-state helpers, freshness rules.
- Consistent API error envelope, pagination, JSON logging, health and readiness.
- `/system/config/` and `/system/data-status/` expose capability and credential
  state without leaking secrets.
- OpenAPI schema generated from code and validated clean.
- Ruff configuration and frontend ESLint/TypeScript rules.

**Exit criteria:** `manage.py check`, `pytest`, `ruff`, and schema validation all
pass. **Met.**

---

## Milestone 1 — Kolkata geography and analytical grid

**Status: Done (with a documented data caveat)**

- Import OSM relation 9381363 as the city boundary (ODbL, ~200 km²).
- Import 124 OSM locality points as neighbourhoods (points, not wards).
- Generate the deterministic `KMC-1KM-V1` 1 km grid in EPSG:32645, clipped to
  the boundary, with 250 cells and stable codes.
- Expose area list/detail, neighbourhood search, and grid-cell GeoJSON.
- Attribute all geography to OpenStreetMap and state that the boundary is not
  official KMC data.

**Caveat:** There is no official KMC ward boundary in the repository. Ward-level
statistics are therefore not available and must not be implied.

**Exit criteria:** re-running bootstrap is idempotent; grid codes and geometry
are stable. **Met.**

---

## Milestone 2 — Weather, rainfall, and climate history

**Status: Done**

- Live Open-Meteo current/forecast ingestion (no key required).
- ERA5-Land daily archive ingestion through Open-Meteo, labelled ~9 km
  reanalysis rather than station data.
- Current weather, forecast, and bounded history endpoints with freshness state.
- Rainfall forecast summary and historical monthly aggregation derived from the
  same records; no separate rain-gauge claim.
- Climate metrics for annual/seasonal temperature, precipitation, hot days, and
  heavy-rain days, with a 1991–2020 baseline and descriptive OLS trend.

**Exit criteria:** commands populate real data; API returns `AVAILABLE` with
provenance; stale records are labelled `STALE`. **Met.**

---

## Milestone 3 — Official warnings (IMD)

**Status: Blocked on credential**

- IMD provider adapter, payload normalizer, alert model, serializer, and
  `fetch_alerts` command implemented.
- The feed is labelled official and is never mixed with forecasts or community
  reports.
- Without `IMD_API_KEY`, the endpoint returns `UNAVAILABLE`, an empty list, and
  the missing-credential reason.

**Blocker:** No IMD API key. The authentication header name
(`IMD_API_KEY_HEADER`, default `X-API-Key`) also needs confirmation from IMD
documentation or an account representative; a live probe returned
`{"error":"API key missing"}`.

**Next actions when unblocked:** confirm base URL/header, run a probe with a
real key, add a recorded-payload test for the confirmed shape, schedule
`fetch_alerts`, and observe expiry handling.

---

## Milestone 4 — Air quality (CPCB)

**Status: Blocked on credential**

- CPCB/data.gov.in adapter, station and measurement models, normalizers, and
  `fetch_cpcb` command implemented.
- Nearest-station sorting by haversine distance; measurements retain station
  time and source. Values are never interpolated into a fake neighbourhood AQI.
- Without `CPCB_API_KEY`, no stations and no AQI are shown.

**Blocker:** No `CPCB_API_KEY`; `api.data.gov.in` timed out during probing.

**Next actions when unblocked:** confirm the resource ID and field names against
the live API, ingest stations, verify pollutant units and averaging periods,
then add a "last updated" display and staleness rules per pollutant.

---

## Milestone 5 — Satellite heat and environment

**Status: Blocked on credentials and dataset**

- Landsat scene and 1 km cell observation models; ingestion command with
  dataset validation; layer, observation, cell-detail, and hotspot endpoints.
- Earth Engine export script (`ml/src/heat/gee_landsat_export.py`) for LST,
  NDVI, NDBI, MNDWI, and valid-pixel fraction.
- Layers and hotspots return `UNAVAILABLE` with a reason when no observations
  exist.

**Blocker:** No Earth Engine project/service-account credentials and no grid
asset in Earth Engine. No real export has run.

**Next actions when unblocked:** upload/register the grid asset, run a
dry-season export, ingest it, validate cell coverage and cloud masking, then
publish layer dates and quality flags in the UI.

---

## Milestone 6 — Heat ML predictions

**Status: Not started (pipeline and serving are Done)**

- Artifact-driven pipeline: feature construction, chronological holdout
  training with XGBoost, evaluation, manifest and metrics, prediction export.
- Registration gate rejects missing/invalid artifacts and verifies dataset
  size, date count, split type, and dataset hash.
- Prediction-run ingestion and hotspot/prediction/model-info APIs implemented.
- No model artifact has been trained on real data; no metrics are displayed.
  Synthetic fixtures are used only in tests.

**Blocker:** Milestone 5. Labelled satellite observations are a prerequisite for
training.

**Next actions:** ingest at least one full season of real observations, train,
review metrics and feature importance, register as a non-operational version,
compare against the descriptive hotspot baseline, then promote only if the
evaluation is defensible.

---

## Milestone 7 — Community reports and moderation

**Status: Done**

- Authenticated submission with category, description, time, coordinates, area,
  optional neighbourhood/address, and up to four images.
- Image MIME/extension validation, size limits, re-encoding, and EXIF stripping.
- Public feed with `UNVERIFIED` labelling; rejected/duplicate/expired reports
  hidden; owner and moderator visibility rules.
- Duplicate hints at 250 m / 6 h, shown as suggestions only.
- Moderator-only transitions with an immutable status history.
- Owner edit policy, throttling, map/list/detail pages, and a 7-day summary
  endpoint.

**Exit criteria:** submission, moderation, visibility, duplicate hints, and
upload handling are covered by tests. **Met.**

**Known gaps:** no moderator assignment/SLA, no reporter reputation, no
subscriptions or notifications, no public appeal flow, no account deletion or
data-erasure tooling.

---

## Milestone 8 — Evidence-backed insights

**Status: Done**

- Versioned deterministic rule engine. Rules cover verified waterlogging,
  heavy-rain forecast, heat, air quality, and satellite hotspots, with explicit
  thresholds.
- Every insight carries severity, validity, source, observation time, and
  freshness for each evidence item.
- Missing modules produce a data-availability caveat; no inferred condition is
  invented.
- Read-time generation plus moderator-only persistence and public history.

**Exit criteria:** rule thresholds and evidence behaviour are tested; unavailable
modules do not produce false positives. **Met.**

---

## Milestone 9 — Frontend product

**Status: Done (production polish Partial)**

- All routes implemented: home, weather, alerts, air quality, heat, rainfall,
  climate, reports list/detail/form, insights, methodology, login/register,
  account, not-found.
- Typed API client and query hooks; auth context; provenance panels; data-state
  badges; explicit empty/unavailable states.
- Maps with OSM tiles and visible attribution; location picker; incident map;
  grid-cell map; charts for weather, rainfall, air quality, and climate.
- Responsive layout, accessible form labels, keyboard-operable controls.
- Vite build and Nginx Docker image.

**Remaining polish:** bundle splitting (the main chunk is ~1.1 MB), a manual
browser accessibility pass, skeleton loaders, offline/PWA behaviour, Bengali
localisation, and an end-to-end browser test suite.

---

## Milestone 10 — Operations and production readiness

**Status: Partial**

- Docker Compose with PostGIS, Django, and Nginx; healthchecks; named volumes.
- Environment template, Makefile, logging, media handling, and documented
  commands.
- Health/readiness distinguish liveness from database readiness.

**Gaps before a real launch:**

- Move geometry to native PostGIS and add spatial indexes (ADR-003).
- Replace `runserver` with Gunicorn/Uvicorn and a reverse proxy in production.
- Add a scheduler (cron/Task Scheduler/sidecar) for ingestion with alerting on
  failures.
- Object storage or backed-up media volume; database backup/restore drill.
- Secret management, HTTPS, secure cookies, HSTS, and rate limiting at the edge.
- Error monitoring and uptime checks.
- Retention policy for community reports, images, and logs; account deletion.

---

## Milestone 11 — Documentation and quality gates

**Status: Done (living documents)**

- README with honest status matrix and credentials.
- Architecture, data sources, ML methodology, API, operations, testing,
  decisions, limitations, and this roadmap.
- Backend, ML, and frontend test suites; linting; schema validation; production
  build check.
- The docs distinguish implemented, blocked, and not-started capabilities.

**Exit criteria:** a new contributor can run the stack from the README and
understand what is real. **Met.**

---

## Milestone 12 — Pilot, partnerships, and public launch

**Status: Not started**

This milestone is intentionally untouched. It requires organisational work that
cannot be fabricated in code: an official data-sharing agreement with KMC/IMD/
CPCB, a moderation policy and staffing plan, legal review of privacy and
liability, accessibility certification, and a public communication plan.

**Entry criteria:** Milestones 3–6 unblocked with licensed/official data, and
Milestone 10 gaps closed. Until then the product remains decision support, not
an official warning service.

---

## Phase 2 - Real data onboarding and model training

**Status: Ready to start; blocked on credentials and datasets**

The application, provider interfaces, ingestion commands, registry, and model
pipeline are in place. The next phase is operational rather than architectural:

1. Obtain and verify IMD access; run `fetch_alerts` and confirm official warning
   provenance, expiry, and an honest empty state.
2. Obtain a data.gov.in key; run `fetch_cpcb --max-pages 2`, validate the live
   resource schema and units, then ingest stations with real coordinates.
3. Provision Earth Engine, export the versioned 1 km grid with
   `export_grid_geojson`, upload it as a table asset, and run one Landsat
   export.
4. Ingest the real Landsat table and verify scene dates, grid coverage, and
   provenance in the environmental APIs.
5. Train the LST model only after the quality gates pass; add a spatial or
   scene-level hold-out, compare against a naive baseline, and report metrics by
   season as well as overall.
6. Register the reviewed artifact as non-operational, then promote it only after
   a documented review.

The complete commands, credential checklist, verification gates, and
accuracy/validation protocol are in
[docs/DATA_ONBOARDING.md](DATA_ONBOARDING.md).

**Exit criteria:** each provider module reports `AVAILABLE` from real ingested
records, failures and stale data remain visible, and any model metrics come from
a real evaluated artifact with a recorded dataset hash and date range.

---

## Suggested next increments

Ordered by value and dependency:

1. **PostGIS migration spike** — move `Area.boundary` and `GridCell.geometry`
   to native geometry fields behind the existing serializers, then benchmark
   point-in-polygon and bbox queries.
2. **Scheduled ingestion** — a small scheduler with retries, last-run metrics,
   and an operator-visible failure state; wire it to `/system/data-status/`.
3. **Alert onboarding** — obtain IMD credentials, confirm the contract, and
   add a recorded-payload test before scheduling.
4. **Satellite export** — provision Earth Engine access, export one scene, and
   validate the ingestion path end to end.
5. **Moderation operations** — assignment, queue sorting, SLA, and an audit
   export for moderators.
6. **Frontend performance and accessibility** — route-level code splitting,
   Lighthouse pass, and a Playwright smoke suite.
7. **Privacy and retention** — account deletion, media retention, and a
   published community-report policy.
