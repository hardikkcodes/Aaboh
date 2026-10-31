# API guide

The API is a Django REST Framework application. `schema.yaml` at the repository
root is generated from the running code and is the authoritative contract for
request and response shapes. Interactive docs are served by the backend at
`/api/docs/` (Swagger UI) and `/api/redoc/`.

- **Base path:** `/api/v1/`
- **Schema:** `/api/schema/`
- **Content type:** JSON unless uploading report images (`multipart/form-data`)
- **Timestamps:** ISO 8601 UTC (`Z`), including records that are displayed in
  Asia/Kolkata by the client
- **Dates:** `YYYY-MM-DD`
- **IDs:** UUID strings except grid cells, which also expose a stable `code`

The local backend runs at `http://127.0.0.1:8000` by default; examples below use
that host.

---

## Conventions

### Data state

Environmental responses carry a `state` field:

| State | Meaning |
| --- | --- |
| `AVAILABLE` | Data is present and within its freshness window |
| `PARTIAL` | Some components are missing; available values are still returned |
| `STALE` | Data exists but is older than the freshness window |
| `UNAVAILABLE` | No usable data; `reason` explains why and results are empty |
| `PROCESSING` | A job is running; no result yet |
| `INVALID` | Data failed validation and is not shown as usable |

`UNAVAILABLE` is a normal response, not an error. The API returns HTTP 200 with
an empty result and a `reason` when a provider is not configured.

### Provenance

Most payloads include a `source` object:

```json
{
  "slug": "open_meteo",
  "name": "Open-Meteo",
  "provider_type": "forecast_model",
  "is_official": false,
  "attribution": "Weather data by Open-Meteo.com",
  "license_name": "Creative Commons Attribution 4.0 (CC BY 4.0)",
  "spatial_resolution_m": null,
  "dataset": "Open-Meteo forecast"
}
```

`provider_type` is one of `official`, `forecast_model`, `reanalysis`,
`earth_observation`, `community`, or `supplementary`. `is_official` is only
true for government warnings/measurements. Never treat a forecast, reanalysis
product, satellite estimate, or community report as an official warning.

### Errors

All handled errors use one envelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Validation failed.",
    "details": {
      "area": ["Unknown area: atlantis"]
    }
  }
}
```

Common codes: `validation_error` (400), `not_authenticated` (401),
`permission_denied` (403), `not_found` (404), `method_not_allowed` (405),
`conflict` (409), `throttled` (429), `internal_error` (500). Domain endpoints may
return a more specific code such as `invalid_variable`.

### Pagination

List endpoints that use DRF pagination return:

```json
{
  "count": 120,
  "next": "http://127.0.0.1:8000/api/v1/incidents/?page=2",
  "previous": null,
  "results": []
}
```

Page size defaults to 50. Some endpoints (areas, grid cells, measurements,
insights) return an explicit `count`/`results` envelope or a bare list and are
documented individually.

### Authentication

Token authentication is used by the SPA. Send:

```
Authorization: Token <token>
```

Obtain a token with `POST /api/v1/auth/register/` or `POST /api/v1/auth/login/`.
Session authentication is also enabled for the Django admin. Public reads do not
require authentication.

Throttles: anonymous `120/min`, authenticated `600/min`, auth endpoints
`10/min`, report creation `12/hour`.

---

## System

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/v1/` | Service metadata and endpoint index |
| GET | `/api/v1/health/` | Liveness plus database/spatial engine status |
| GET | `/api/v1/health/ready/` | Readiness; returns 503 when the database is not usable |
| GET | `/api/v1/system/config/` | Branding, city, timezone, provider credential state |
| GET | `/api/v1/system/data-status/` | Per-module state, last success, and reasons |

`/system/data-status/` is the quickest way to see why a page is empty. It reports
whether each provider is configured without exposing secret values.

---

## Locations

| Method | Path | Query parameters |
| --- | --- | --- |
| GET | `/api/v1/areas/` | `level` (optional) |
| GET | `/api/v1/areas/<slug>/` | — |
| GET | `/api/v1/areas/<slug>/grid-cells/` | `version` (optional) |
| GET | `/api/v1/locations/search/` | `q` (2+ characters matches by name; empty returns 20 localities) |

Area detail returns the boundary GeoJSON, neighbourhood list, and grid versions.
Grid cells are returned in EPSG:4326 (GeoJSON), generated in EPSG:32645. Each
cell includes `coverage_fraction` and `area_km2`; filter low-coverage edge cells
for analysis.

```bash
curl "http://127.0.0.1:8000/api/v1/areas/kolkata/grid-cells/"
```

---

## Place status

| Method | Path | Query parameters |
| --- | --- | --- |
| GET | `/api/v1/place-status/` | `area` (default `kolkata`), `neighbourhood` (optional) |
| GET | `/api/v1/areas/<slug>/place-status/` | `neighbourhood` (optional) |

One area-first response composes the modules a resident needs: `weather`, `rain`
(next 24 hours), `recent_rain` (yesterday's archive day plus today), `waterlogging`,
`heat` (air and land surface), `air_quality` (nearest CPCB station), `alerts`,
`reports` (nearby public submissions), `coverage`, and a short `status` summary.
Every section carries `state`, its source, timestamps, and a `reason` when it is
unavailable. `place.resolution` is `area` or `neighbourhood`; the search radius is
5 km for an area and 2.5 km for a neighbourhood.

`waterlogging` is a transparent point score, not a model:

| Input | Maximum points |
| --- | --- |
| Forecast rain, next 24 h | 3 |
| Highest daily rain, recent 48 h | 2 |
| Verified nearby water reports | 2 |
| Unverified nearby water reports | 1 |

Levels are `low` (<2), `elevated` (2–3), and `high` (4+). If rainfall inputs are
missing, the level is `reports_only` when reports exist and `unknown` otherwise.
The response states `method.is_ml = false` and includes caveats. It must not be
described as a trained prediction, a probability, or an official flood warning.

```bash
curl "http://127.0.0.1:8000/api/v1/areas/kolkata/place-status/?neighbourhood=park-street"
```

---

## Weather

| Method | Path | Query parameters |
| --- | --- | --- |
| GET | `/api/v1/weather/current/` | `area` (default `kolkata`) |
| GET | `/api/v1/weather/forecast/` | `area`, `hours` (1–96, default 48) |
| GET | `/api/v1/weather/history/` | `area`, `start_date`, `end_date` (max 730 days) |
| GET | `/api/v1/weather/locations/` | `area` |

Current conditions are an Open-Meteo forecast/analysis point, not an official
station observation. History is ERA5-Land reanalysis at roughly 9 km resolution.
A record older than three hours is `STALE` for current/forecast endpoints.

```json
{
  "area": { "slug": "kolkata", "name": "Kolkata Municipal Corporation" },
  "state": "AVAILABLE",
  "source": { "slug": "open_meteo", "provider_type": "forecast_model" },
  "observed_at": "2026-10-30T12:00:00Z",
  "retrieved_at": "2026-10-30T17:44:59Z",
  "record": {
    "kind": "CURRENT",
    "temperature_c": 25.6,
    "apparent_temperature_c": 31.8,
    "relative_humidity": 97.0,
    "precipitation_mm": 0.1
  },
  "note": "Current conditions are a provider forecast/analysis point, not an official station observation."
}
```

(Example abbreviated; the real record contains all available weather fields and
nulls for values the provider did not return.)

---

## Rainfall

| Method | Path | Query parameters |
| --- | --- | --- |
| GET | `/api/v1/rainfall/forecast/` | `area` |
| GET | `/api/v1/rainfall/history/` | `area`, `days` (7–730, default 90) |

Forecast returns a 24-hour total, maximum probability, peak hour, hourly values,
and three daily values. History returns total, wet days, maximum daily value,
monthly aggregation, and daily records. Forecast rainfall is **not** a flood or
waterlogging prediction; community reports and official warnings are separate.

---

## Official alerts

| Method | Path | Query parameters |
| --- | --- | --- |
| GET | `/api/v1/alerts/` | `hazard`, `severity`, `current` (default `true`) |
| GET | `/api/v1/alerts/<uuid>/` | — |

Only IMD warnings are returned. In the current environment there is no
`IMD_API_KEY`, so the list is `UNAVAILABLE` with `count: 0` and a reason. Absence
of a warning is **not** proof that conditions are safe.

---

## Air quality

| Method | Path | Query parameters |
| --- | --- | --- |
| GET | `/api/v1/air-quality/stations/` | `area`, or `lat` + `lon`, `nearest=true` |
| GET | `/api/v1/air-quality/measurements/` | `station`, `station_name`, `hours` (1–2160, default 24) |

Stations are sorted by distance from the area centroid (or supplied point) and
include measurements from the last seven days. AQI is never interpolated into a
neighbourhood surface. Without `CPCB_API_KEY`, stations and measurements are
`UNAVAILABLE`.

---

## Satellite environment

| Method | Path | Query parameters |
| --- | --- | --- |
| GET | `/api/v1/environment/layers/` | — |
| GET | `/api/v1/environment/observations/` | `variable` (`lst_c`, `ndvi`, `ndbi`, `mndwi`), `date` |
| GET | `/api/v1/environment/cells/<cell_code>/` | — |

`/observations/` returns a GeoJSON `FeatureCollection`. If `date` is omitted, the
latest available date is used. Values are pixel aggregations into 1 km cells;
the native Landsat resolution is not 1 km. `lst_c` is land-surface temperature,
not air temperature. All layers are `UNAVAILABLE` until a real export is
ingested.

---

## Heat

| Method | Path | Query parameters |
| --- | --- | --- |
| GET | `/api/v1/heat/hotspots/` | `area` |
| GET | `/api/v1/heat/predictions/` | `area` |
| GET | `/api/v1/heat/model-info/` | — |

`/hotspots/` is descriptive: cells at or above the 90th percentile of observed
LST for the latest scene date. `/predictions/` is model output and requires a
completed prediction run. `/model-info/` only reports metrics produced by a
registered evaluated artifact. All three return `UNAVAILABLE` in the current
environment. Predicted or observed LST is never described as air temperature or
an official heat warning.

---

## Climate

| Method | Path | Query parameters |
| --- | --- | --- |
| GET | `/api/v1/climate/metrics/` | `area`, `variable`, `period_type`, `season`, `year` |
| GET | `/api/v1/climate/trends/` | `area` |

Metrics include annual and seasonal temperature, precipitation, hot days
(≥ 35 °C), and heavy-rain days (≥ 50 mm), with a 1991–2020 baseline and anomaly.
Trends are ordinary-least-squares slopes on annual values, returned with a
caveat. The data is ~9 km ERA5-Land reanalysis; do not present it as 1 km local
observation.

---

## Community reports

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/incidents/` | Public | List visible reports |
| POST | `/api/v1/incidents/` | Required | Submit a report |
| GET | `/api/v1/incidents/summary/` | Public | 7-day counts by status/category |
| GET | `/api/v1/incidents/<uuid>/` | Public | Detail, including duplicate hints |
| PATCH | `/api/v1/incidents/<uuid>/` | Owner/moderator | Edit while `SUBMITTED` or `UNDER_REVIEW` |
| GET | `/api/v1/incidents/live/` | Public | Current reports as GeoJSON; filters: `area`, `category` |
| POST | `/api/v1/incidents/<uuid>/confirm/` | Required | Vote `still_there`, `cleared` or `wrong` |
| GET | `/api/v1/incidents/<uuid>/history/` | Public | Status history without moderator identity; notes only for moderators and the reporter |
| POST | `/api/v1/incidents/<uuid>/moderate/` | Moderator | Change status |

**List filters:** `mine=true` (authenticated), `category`, `status`, `area`,
`neighbourhood`, `since_hours` (1–2160), `bbox=min_lon,min_lat,max_lon,max_lat`.

**Categories:** `waterlogging`, `flooding`, `blocked_drainage`, `fallen_tree`,
`road_disruption`, `power_cut`, `stagnant_water`, `environmental_hazard`, `other`.

**Live reports:** each report has `expires_at`, set by category (for example 6
hours for waterlogging and power cuts, 7 days for stagnant water). A `still_there`
vote extends it, up to four lifetimes after `occurred_at`. A report leaves the map
after two independent `cleared` votes, or one from the reporter or a moderator.
Reporters can't confirm their own reports. `trust` is `unconfirmed`,
`resident_confirmed` (two other residents) or `moderator_verified`; residents
can't change `verification_state`. Live map coordinates are rounded to 4 decimals.

**Create fields (JSON):**

```json
{
  "area": "kolkata",
  "neighbourhood": "salt-lake",
  "category": "waterlogging",
  "description": "Knee-deep water across the road near the market.",
  "occurred_at": "2026-10-30T16:35:00Z",
  "latitude": 22.521,
  "longitude": 88.3545,
  "address_text": "Near the main market crossing"
}
```

`description` is optional, except for `other`, and is 10–2000 characters when
present. `water_depth` and `passability` are optional and apply only to
`waterlogging` and `flooding`. `occurred_at` must be within the last 7 days and not
in the future. The point must fall inside the selected area boundary. `address_text`
is a coarse landmark only; house numbers and contact details are rejected.

For images, send `multipart/form-data` with up to four `attachments` fields. The
server validates the MIME type and size, re-encodes the image, and strips EXIF.
Reporters' identities and emails are never returned publicly. New reports are
`SUBMITTED` and labelled `UNVERIFIED`.

**Moderation body:**

```json
{
  "status": "VERIFIED",
  "note": "Confirmed by field volunteer.",
  "is_public": true,
  "duplicate_of": null
}
```

Allowed transitions are enforced by the service layer. `DUPLICATE` requires a
`duplicate_of` id. Only moderators can moderate; every transition is audited.

---

## Insights

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/insights/` | Public | Generate insights from current evidence |
| POST | `/api/v1/insights/generate/` | Moderator | Generate and persist a snapshot |
| GET | `/api/v1/insights/history/` | Public | Persisted snapshots |
| GET | `/api/v1/insights/<uuid>/` | Public | One persisted insight |

Get parameters: `area`, `rule`, `severity`. Each insight includes `rule_id`,
`kind`, `title`, `body`, `severity`, validity, and an `evidence` array. Evidence
items carry source, observed time, and freshness. When a module is unavailable,
the response includes a data-availability caveat and the rule is skipped rather
than inferred.

---

## Accounts

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/register/` | Public | Create account; returns token + user |
| POST | `/api/v1/auth/login/` | Public | Obtain token |
| POST | `/api/v1/auth/logout/` | Required | Delete the current token |
| GET/PATCH | `/api/v1/users/me/` | Required | Profile |
| PATCH | `/api/v1/users/me/preferences/` | Required | `default_area`, `temperature_unit` |
| GET/POST | `/api/v1/users/me/saved-locations/` | Required | List/create saved locations |
| DELETE | `/api/v1/users/me/saved-locations/<uuid>/` | Required | Delete own saved location |

Registration requires `email` and `password` (validated with Django's password
validators; minimum length 10) and accepts an optional `display_name`. Login
does not reveal whether an email exists. Email verification and password reset
are not implemented.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"..."}'
```

---

## Regenerating the schema

After changing serializers or views:

```powershell
cd backend
.venv\Scripts\python.exe manage.py spectacular --file ..\schema.yaml --validate
```

A clean run must produce no warnings. Treat schema validation as part of the
test gate; the frontend types in `frontend/src/api/types.ts` should be updated in
the same change.
