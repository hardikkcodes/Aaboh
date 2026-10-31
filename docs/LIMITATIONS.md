# Limitations and honest gaps

This document lists what the platform does **not** do, what is unverified, and
which claims must not be made. It is deliberately blunt. If a statement here
conflicts with marketing copy, this document wins.

---

## 1. Data and provider limitations

| Area | Limitation | Consequence |
| --- | --- | --- |
| Official warnings | No IMD API key; the auth header is unconfirmed | The alerts page is empty and `UNAVAILABLE`. The platform cannot warn anyone. |
| Air quality | No CPCB/data.gov.in key; the host timed out during probing | No stations, no AQI, no pollutant history. |
| Satellite heat | No Earth Engine credentials or registered grid asset; no real export has run | Heat/environment layers are `UNAVAILABLE`; there is no LST map. |
| Heat ML | No labelled satellite dataset, no trained artifact | No predictions and no metrics are displayed. |
| Weather | Open-Meteo model output, not a station observation | Temperature/rain values are gridded model data; local microclimates can differ. |
| Climate | ERA5-Land reanalysis at ~9 km through Open-Meteo | Annual/seasonal metrics are area-level, not neighbourhood observations. |
| Rainfall | Derived from weather forecast/archive, not a rain gauge | No flood prediction; no street-level waterlogging inference from rainfall alone. |
| Waterlogging signal | Rule-based points over forecast rain, recent daily rain, and nearby reports | Not a trained model, not a probability, and not a flood forecast. It does not know drain capacity, elevation, tide, or pumping. |
| Waterlogging ML | No historical street-level labelled dataset, terrain/drainage features, or verified event labels | No trained waterlogging model, no accuracy claim, and no neighbourhood susceptibility map. |
| Geography | OSM relation, not an official KMC boundary; localities are points | The ~200 km² area and 124 localities are community-maintained. There are no official wards or ward statistics. |
| Grid | 1 km analytical cells, clipped to the boundary | Edge cells have partial coverage; satellite values are aggregations, not 1 km native measurements. |
| Air quality geography | Stations are point locations | Values are never interpolated into a neighbourhood surface. |
| Time zones | API timestamps in UTC; some aggregations use Asia/Kolkata | Consumers must convert deliberately; the UI does. |

**Do not claim:** "official KMC boundary", "ward-level data", "real-time official
alerts", "CPCB AQI for every neighbourhood", "1 km satellite measurements", or
"90% accurate heat predictions". None of these are supported.

---

## 2. What "unavailable" means

An empty page is usually correct behaviour, not a bug. When a provider is not
configured or has no data, endpoints return HTTP 200 with `state:
"UNAVAILABLE"`, an empty result, and a `reason`. `/api/v1/system/data-status/`
explains which credential or dataset is missing.

The application does not fall back to synthetic values, cached demo numbers, or
interpolated guesses. Tests use synthetic fixtures **only** inside the test
database.

---

## 3. Spatial and infrastructure limits

- **Place status is not street-level.** An area status uses the Kolkata forecast
  point and a 5 km report radius; a neighbourhood status uses the locality point
  and a 2.5 km radius. Two nearby streets can differ, and the response says so.
- **No native PostGIS/GeoDjango in development.** Geometry is stored as
  validated GeoJSON and spatial predicates run in Python via Shapely/pyproj
  (ADR-003). This is unindexed and fine for one city / 250 cells, not for
  multi-city or high-volume spatial queries.
- **Docker stack unverified in this environment.** Compose, PostGIS, and the
  Nginx frontend image are provisioned and documented, but there is no Docker
  daemon on the build machine, so the stack has not been executed end to end.
- **Development server only.** The Compose backend uses `runserver`; there is no
  Gunicorn/Uvicorn, TLS termination, HSTS, secure-cookie configuration, or edge
  rate limiting.
- **No scheduler.** Ingestion is manual or external (Task Scheduler/cron).
  Freshness depends on that external job; the API marks stale data but cannot
  refresh itself.
- **No caching layer.** Every read hits the database and recomputes insights.
  This is acceptable at current scale but will not handle high traffic.
- **SQLite concurrency.** Development uses SQLite; concurrent writes can lock.
  PostgreSQL is the production target.
- **No object storage.** Report images live on the local filesystem / Docker
  volume. There is no CDN, virus scanning, or automated lifecycle policy.

---

## 4. ML limitations

- No real model exists. The pipeline, gates, registration, ingestion, and
  serving paths are implemented and tested, but there is no trained artifact and
  no metric.
- The documented target is **land-surface temperature (LST)**, not air
  temperature. Even a perfect LST model would not be an air-temperature
  measurement or an official heat warning.
- The training gate requires at least 500 rows, 20 distinct dates, and 10 test
  dates. A short or single-season dataset is rejected by design.
- Validation is a chronological holdout, not spatial cross-validation. Spatial
  autocorrelation can make held-out scores optimistic; this is a known
  methodological limitation, not a solved problem.
- No uncertainty intervals, calibration, drift monitoring, or fairness analysis
  are shipped. Do not present point predictions as certainties.
- Hotspot analysis (90th percentile of observed LST) is descriptive and is not
  the ML model.

---

## 5. Community reporting limitations

- Reports are **unverified resident observations**, not official alerts. The UI
  labels them, but downstream consumers must preserve that label.
- Moderation is manual. There is no assignment, SLA, escalation, trusted-reporter
  tier, or appeal flow. A small team cannot guarantee timely review.
- Duplicate detection is a hint (250 m / 6 h) and never auto-merges. Near
  duplicates can remain visible.
- There is no notification/subscription system; users must revisit the site.
- There is no account deletion, data export, or automated retention policy.
  Deleting a report or image requires operator intervention.
- Reporter email/identity is stored and hidden from public serializers, but
  there is no formal privacy impact assessment, encryption-at-rest guarantee, or
  data-processing agreement.
- Image validation, re-encoding, and EXIF stripping are implemented, but uploads
  are not malware-scanned.
- Rate limits are per-process DRF throttles (12 reports/hour/user); they are not
  a defence against a distributed abuse campaign.

---

## 6. Application and UX limitations

- No email verification, password reset, MFA, or account recovery. Accounts are
  development-grade.
- Tokens are stored client-side by the SPA. This is acceptable for the current
  scope but is weaker than httpOnly cookies with CSRF protection.
- No internationalisation. The interface is English-only; Bengali labels and
  local terminology are not implemented.
- No offline/PWA support; the map requires network access for tiles.
- The production JS bundle is a single large chunk (~1.1 MB) with no route-level
  code splitting.
- No formal accessibility audit or certification. Forms have labels and controls
  are keyboard-operable, but this is not WCAG conformance.
- No analytics, error tracking, or user feedback loop.
- No browser end-to-end tests. Frontend coverage is unit/component level.
- No pagination UI for very long lists beyond the API defaults; the report list
  is not virtualised.
- The header search navigates to the reports page with area/name parameters;
  coordinate parameters are currently not used by that page.

---

## 7. Operations and security limitations

- No CI pipeline is committed. The quality commands exist but must be wired to a
  runner.
- No automated backups or tested restore drill. The runbook documents manual
  steps only.
- No uptime monitoring, alerting, or on-call process.
- No secret manager; credentials are environment variables in `.env`.
- No audit log for admin actions beyond incident status history.
- No API version negotiation beyond the `/api/v1/` prefix; breaking changes
  require coordination.
- No load, soak, or penetration testing has been performed.
- The OpenAPI schema is validated, but there is no contract test against the
  frontend types.
- Data retention and deletion policies are not implemented.
- Legal review, terms of service, privacy policy, and accessibility statement are
  not included.

---

## 8. Claims that require external validation

Do not state or imply any of the following without written evidence:

- a partnership with KMC, IMD, CPCB, or any government body;
- that the boundary, wards, or localities are official;
- that a warning shown is official unless it came from the IMD feed with
  `is_official: true`;
- that an AQI value is available for a neighbourhood when only station data
  exists;
- that the heat model has a measured accuracy, until a real evaluated artifact
  is registered;
- that the platform is a flood early-warning system;
- that community reports are verified unless a moderator set that status;
- that the service is suitable for emergency decisions.

The product is **decision support** and a demonstration of an honest data
pipeline. It is not an official warning service or medical advice. Always follow
IMD, KMC, and emergency services.

---

## 9. How to close the biggest gaps

1. Obtain IMD and CPCB credentials; confirm contracts and payloads; schedule
   ingestion.
2. Provision Earth Engine access; export and ingest one real Landsat season.
3. Train and evaluate a heat model on that dataset; register it as
   non-operational first.
4. Move to PostGIS and replace `runserver` with a production server.
5. Add scheduling, monitoring, backups, and a tested restore.
6. Publish privacy, retention, moderation, and accessibility policies.
7. Commission an independent review of the boundary, grid, and any public
   claims before launch.

See [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) for milestone-level detail.
