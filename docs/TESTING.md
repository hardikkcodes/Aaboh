# Testing strategy

The test suite exists to protect two things: **behaviour** (moderation,
visibility, permissions, ingestion gates) and **honesty** (no fabricated values,
no metrics without an evaluation, no silent substitution when a provider is
missing).

Tests run offline. They do not call Open-Meteo, IMD, CPCB, or Earth Engine, and
they do not depend on the bootstrapped Kolkata boundary or live database. That
keeps them fast and deterministic, at the cost of not detecting upstream provider
contract changes; those are caught by running the ingestion commands against a
real environment (see `OPERATIONS.md`).

**Current totals (2026-10-31):** 74 backend tests, 10 ML tests, 10 frontend
tests. Treat these as a snapshot; use the commands below for the current count.

---

## 1. Commands

```powershell
# Backend
cd backend
.venv\Scripts\python.exe -m pytest -q

# ML package
cd ml
..\backend\.venv\Scripts\python.exe -m pytest tests -q

# Frontend
cd frontend
npm.cmd test                 # watch mode
npm.cmd test -- --run        # one-shot / CI
```

Quality gates that should pass before a commit:

```powershell
cd backend
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe manage.py spectacular --file ..\schema.yaml --validate

cd ..\frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
```

`make test` runs backend + frontend tests; `make lint` runs ruff + ESLint +
TypeScript.

---

## 2. Backend tests

Location: `backend/tests/`. Pytest with `pytest-django` and a test database.
`conftest.py` defines the shared fixtures.

### Fixtures and conventions

- A **synthetic rectangular area** (`88.34–88.38`, `22.54–22.58`) instead of the
  real OSM boundary, so tests are independent of bootstrap data.
- A deterministic `TEST-1KM-V1` grid, so grid and satellite tests have stable
  cell codes and geometry.
- A synthetic weather location, neighbourhood, normal user, moderator user,
  authenticated API clients, and an in-memory image upload.
- Time-sensitive assertions use explicit datetimes; avoid `sleep`.
- Provider tests monkeypatch the HTTP layer and feed recorded-shape payloads
  through the real normalizers.

### What is covered

| File | Focus |
| --- | --- |
| `test_core_locations.py` | API root, health/readiness, honest data-status, freshness boundaries, deterministic grid, area/grid endpoints, search |
| `test_accounts.py` | Registration, duplicate email, weak password, login leak resistance, token auth, logout, profile, preferences, saved-location ownership/boundary, schema generation |
| `test_incidents.py` | Auth requirement, image sanitisation and rejection (type, corrupt, oversized, too many), boundary validation, description/time validation, moderation permissions and transitions, duplicate hints, hidden rejected reports, owner edit policy, summary |
| `test_providers_and_normalization.py` | Open-Meteo request bounds/errors and normalisation, IMD key requirement and warning classification, CPCB key requirement, pollutant grouping, AQI category boundaries |
| `test_satellite_and_heat_pipeline.py` | Landsat ingestion provenance, missing acquisition time, unknown cells, artifact evaluation gate, non-operational default, prediction ingestion, refusal to serve unscored models, API disclaimer |
| `test_services_and_insights.py` | Weather states, empty-state honesty for alerts/AQ/environment/heat, rainfall derivation, model metrics only when registered, observed-LST hotspots, caveated insights, evidence provenance, persisted insight permissions, structured errors |
| `test_place_status.py` | Area-first aggregation, honest all-unavailable state, rule-based waterlogging points, verified vs unverified report caps, recent 48-hour rain coverage, unknown-neighbourhood rejection |

### Deliberately not covered

- Real provider HTTP calls (no network in tests).
- Native PostGIS/GeoDjango behaviour (not active; see ADR-003).
- Load/performance characteristics.
- Full browser interaction (frontend tests cover units and shared components;
  use a manual or future Playwright pass for flows).
- Production Nginx/Docker behaviour.

---

## 3. ML tests

Location: `ml/tests/`. Run with the backend virtualenv (it contains Pandas,
NumPy, scikit-learn, XGBoost, and Joblib).

| File | Focus |
| --- | --- |
| `test_features.py` | Required-column validation, missing file, quality filtering, low valid-pixel filtering, time features, chronological split without future leakage, minimum row gate, range validation, prediction-frame requirements and refusal to impute |
| `test_training.py` | Training writes reproducible artifacts (model, metrics, manifest, feature list) and the manifest records the dataset hash and split |

The tests generate small synthetic CSVs with a fixed seed. They verify that the
pipeline **refuses** to proceed on inadequate data, which is the important
safety property. They do not claim that the synthetic model has useful skill.

Model tests do not assert a specific accuracy. Any real metric must come from a
real dataset and be recorded in the artifact; the application displays only what
the artifact contains.

---

## 4. Frontend tests

Location: `frontend/src/test/`. Vitest + Testing Library + jsdom.

| File | Focus |
| --- | --- |
| `format.test.ts` | Temperature conversion keeps units, missing values render as an em dash rather than zero, enum labels are humanised, long text truncation is deterministic |
| `components.test.tsx` | Data-state labels, no notice for available layers, unavailable layer shows the reason and explicit gap, evidence provenance and the unverified community chip stay visible |
| `place.test.tsx` | Area and neighbourhood route construction, place-page rendering, visible rule-based caveat, unavailable CPCB reason, nearby report list |

The setup file imports `@testing-library/jest-dom`. These are unit/component
tests, not end-to-end tests. They intentionally assert that missing values do not
become `0` and that unavailable states remain visible, because those are product
correctness requirements.

---

## 5. Manual smoke checklist

Run this after wiring a real environment or before a release:

1. `manage.py check`, migrations, `bootstrap_kolkata`; confirm 1 area, 124
   localities, 250 cells.
2. `fetch_weather`, `fetch_weather_history`, `fetch_climate`; confirm
   `AVAILABLE` states and non-null provenance.
3. Start the backend and frontend; load every route directly (including a deep
   link such as `/reports/<uuid>` to verify SPA fallback).
4. Confirm the honest states: alerts, air quality, satellite, and heat are
   `UNAVAILABLE` with reasons when unconfigured.
5. Register a user, submit a report with an image, confirm `UNVERIFIED` and EXIF
   stripping; as a moderator, verify it and confirm the status history and
   duplicate hints.
6. Confirm rejected reports disappear from the public list and that another
   user cannot edit or delete them.
7. Check `/api/v1/system/data-status/` after a failed ingestion: the module
   should be `STALE` or `UNAVAILABLE`, never silently healthy.
8. Run the build and serve the Docker frontend if Docker is available; confirm
   `/api` proxying and deep links.

---

## 6. Adding tests

- **New endpoint:** add a happy-path test, an unavailable/empty-state test, and
  an authorisation test. Assert on the error envelope for invalid input.
- **New provider:** test the adapter's request construction and error mapping,
  then the normalizer with a recorded payload. Never call the live API.
- **New rule:** test the threshold boundary on both sides, the evidence shape,
  and the behaviour when an input module is unavailable.
- **New model artifact:** test that registration refuses the invalid cases
  before testing the success path.
- **New UI state:** add a component test that asserts the state label and reason
  are visible; avoid snapshot tests that hide intent.

Keep fixtures small and explicit. Prefer a fixed timestamp over "now" unless the
code under test is specifically about time windows.

---

## 7. Continuous integration sketch

A minimal pipeline:

```yaml
# pseudocode
backend:
  - pip install -r backend/requirements/dev.txt
  - cd backend && python manage.py check
  - cd backend && python -m ruff check .
  - cd backend && python -m pytest -q
  - cd backend && python manage.py spectacular --file ../schema.yaml --validate
ml:
  - cd ml && pytest tests -q
frontend:
  - cd frontend && npm ci
  - npm run lint && npm run typecheck && npm test -- --run && npm run build
```

No CI configuration is committed yet. The commands are the contract; wire them
to the repository host of your choice.
