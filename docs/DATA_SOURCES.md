# Data Sources and Provenance

This document records what each source is, what it may be used for, and what is
actually connected in this repository. Provider identity is stored in the
`DataSource` table and returned with API payloads; the seed migration is
`backend/apps/core/migrations/0002_seed_data_sources.py`.

## Summary matrix

| Slug | Source | Provider type | Official? | Native resolution | Expected refresh | Current status |
| --- | --- | --- | --- | --- | --- | --- |
| `osm` | OpenStreetMap contributors | Supplementary | No | Vector, variable | Continuous | **Working** (boundary + 124 localities) |
| `open_meteo` | Open-Meteo | Forecast model | No | Model-dependent | 180 min | **Working** |
| `imd` | India Meteorological Department | Official | **Yes** | Event/district | 30 min | **Blocked** — no key |
| `cpcb` | CPCB via data.gov.in | Official | **Yes** | Station points | 60 min | **Blocked** — no key |
| `landsat` | USGS/NASA Landsat C2 | Earth observation | No (public authority data) | 30 m optical / 100 m thermal | 16-day revisit | **Blocked** — no GEE credentials/asset |
| `era5_land` | ERA5-Land via Open-Meteo archive | Reanalysis | No | ~9 km | Daily | **Working** |
| `community_reports` | Platform contributors | Community | No | User point | Event-driven | **Working** |
| `development_fixture` | Synthetic test marker | Development fixture | No | n/a | n/a | **Tests only** |

---

## OpenStreetMap (`osm`)

- **Used for:** Kolkata area boundary and named locality points.
- **Boundary:** OSM relation **9381363**, `admin_level=8`, Wikidata **Q1348**.
- **Boundary provenance:** community-maintained, measured at **200.00 km²** by
  the bootstrap command. It is **not** an official KMC boundary or ward map.
- **Localities:** 124 OSM `place` nodes inside the boundary, stored as points.
  These are neighbourhoods, not wards, and have no official status.
- **Licence:** ODbL 1.0. Attribution: © OpenStreetMap contributors.
- **API metadata:** includes `source_ref`, Wikidata, licence and a caveat that
  the boundary should be replaced with an official KMC dataset when available.
- **Operational note:** the bootstrap can re-import from local GeoJSON files
  (`backend/apps/locations/data/kolkata_boundary.geojson` and
  `kolkata_localities.geojson`) using `bootstrap_kolkata`.

## Open-Meteo (`open_meteo`)

- **Used for:** current conditions, hourly and daily forecasts, daily historical
  archive (last 730 days), and rainfall forecast/history.
- **Type:** provider forecast model / archive API. **Not** an official station
  observation and **not** an official warning.
- **Key:** none required. `OPEN_METEO_ENABLED` defaults to true.
- **Refresh expectation:** 180 minutes; current/forecast responses become
  `STALE` after 3 hours since retrieval.
- **Resolution:** Open-Meteo chooses the best available model per point; native
  grid spacing varies by variable. The platform deliberately does **not** assert
  a single resolution.
- **Licence:** CC BY 4.0. Attribution: “Weather data by Open-Meteo.com”.
- **Commands:** `fetch_weather`, `fetch_weather_history`.
- **Live verification:** forecast and archive requests were executed
  successfully during development without a key.

## India Meteorological Department (`imd`)

- **Used for:** official weather warnings (heavy rain, thunderstorm, heatwave,
  cold wave, cyclone, fog, flood, other).
- **Type:** official Government of India warnings. If shown, they are the only
  records labelled as official alerts.
- **Access:** public API at `https://api.imd.gov.in/api/v1` returned
  `{"error":"API key missing"}` during probing. A key is required.
- **Credential:** `IMD_API_KEY`. The API-key header name is **not confirmed**;
  the adapter defaults to `X-API-Key` and accepts `IMD_API_KEY_HEADER`.
- **Refresh expectation:** 30 minutes; event-driven.
- **Current state:** adapter, normaliser and `fetch_alerts` command are
  implemented, but no key is configured. `/api/v1/alerts/` therefore returns
  `UNAVAILABLE` with an explicit reason. No sample warnings are seeded.
- **Licence/attribution:** IMD terms of use; “India Meteorological Department”.
- **Handling of unmapped fields:** the normaliser preserves unknown severity or
  certainty as `UNKNOWN`/partial quality rather than inventing values.

## Central Pollution Control Board (`cpcb`)

- **Used for:** station-based air-quality measurements (AQI, PM2.5, PM10, NO2,
  SO2, CO, O3).
- **Type:** official station observations. Values remain station-specific. The
  platform does **not** interpolate an AQI surface or claim neighbourhood AQI.
- **Access:** data.gov.in resource
  `3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69`. `api.data.gov.in` timed out during the
  development probe.
- **Credential:** `CPCB_API_KEY` (required). No key is configured.
- **Current state:** adapter, pollutant grouping, AQI category boundaries and
  `fetch_cpcb` command are implemented. No stations or measurements are seeded,
  so `/api/v1/air-quality/stations/` returns `UNAVAILABLE`.
- **Refresh expectation:** 60 minutes; typically hourly station reports.
- **Licence:** Government Open Data License – India. Attribution: CPCB /
  data.gov.in.

## Landsat Collection 2 (`landsat`)

- **Used for:** land-surface temperature (LST), NDVI, NDBI, MNDWI aggregated to
  the 1 km analytical grid.
- **Collections:** `LANDSAT/LC08/C02/T1_L2` and `LANDSAT/LC09/C02/T1_L2`.
- **Resolution:** 30 m optical; thermal native ~100 m (resampled to 30 m in the
  Collection 2 Level 2 product). The 1 km grid is an **aggregation unit**, not
  native measurement resolution.
- **Access:** requires Google Earth Engine:
  `GEE_PROJECT_ID`, `GEE_SERVICE_ACCOUNT_EMAIL`,
  `GEE_SERVICE_ACCOUNT_KEY_FILE`, plus an Earth Engine asset containing the 1 km
  grid. None are configured, and the grid asset does not exist.
- **Current state:** `ml/src/heat/gee_landsat_export.py`,
  `ingest_landsat_observations`, layer/observation APIs, and hotspot logic are
  implemented and tested with synthetic fixtures. No real export has run, so all
  satellite/heat observation endpoints return `UNAVAILABLE`.
- **LST formula:** `LST_C = ST_B10 * 0.00341802 + 149.0 - 273.15`, as documented
  by USGS. Cloud/cloud-shadow/dilated-cloud pixels are masked through `QA_PIXEL`.
- **Quality threshold:** rows with `valid_pixel_fraction < 0.5` are dropped by
  default (configurable on ingestion).
- **Licence:** USGS Landsat data are public domain. Attribution: USGS/NASA
  Landsat.

## ERA5-Land (`era5_land`)

- **Used for:** long-term climate metrics, seasonal/annual temperature and
  precipitation, hot days (≥35 °C), heavy-rain days (≥50 mm), anomalies and
  descriptive linear trends.
- **Access path:** Copernicus ERA5-Land daily aggregates through the Open-Meteo
  archive API. No CDS key is required for this path.
- **Resolution:** approximately **9 km**. All metrics are area-level reanalysis,
  not 1 km or station observations.
- **Refresh expectation:** daily.
- **Baseline:** default 1991–2020, computed from complete years only.
- **Current state:** live metrics were ingested for Kolkata with
  `fetch_climate`. `/api/v1/climate/metrics/` and `/trends/` return real values
  with methodology and resolution caveats.
- **Licence:** Copernicus Climate Change Service licence. Attribution:
  ERA5-Land / Copernicus Climate Change Service.
- **Optional direct CDS adapter:** not implemented; `CDS_API_KEY` is unused.

## Community reports (`community_reports`)

- **Used for:** resident-submitted waterlogging, flooding, blocked drainage,
  fallen trees, road disruption, environmental hazards and other incidents.
- **Type:** community observation, explicitly **not** an official alert.
- **Submission requirements:** authenticated account, category, description
  ≤2000 characters, occurred time, point inside the selected area, optional
  coarse address text (advice: do not enter a home address), up to 4 images.
- **Moderation:** starts as `SUBMITTED`; moderators move through a constrained
  state machine and every transition is recorded. Public reads exclude
  `REJECTED`, `DUPLICATE` and `EXPIRED` unless the viewer is the reporter or a
  moderator.
- **Duplicate hints:** same category within 250 m and ±6 hours; hints never
  auto-merge.
- **Privacy:** reporter email/identity is never exposed publicly. Moderator
  identities are excluded from public history.
- **Image handling:** magic-byte validation, EXIF stripping, max 5 MB, max 4
  files, re-encoded JPEG, SHA-256 stored.
- **Licence:** platform contribution terms (not finalised); attribution
  “Community contributors”.

## Development fixtures (`development_fixture`)

- A reserved provenance marker for **automated tests only**.
- No synthetic environmental data is present in the development database or in
  any API response.
- The source is retained so tests can prove that fixture data is distinguishable
  from real provider data.

## Data we deliberately do not claim

- No official KMC boundary or ward map.
- No IMD warnings without `IMD_API_KEY`.
- No CPCB stations/AQI without `CPCB_API_KEY`.
- No Landsat/GEE observations without Earth Engine credentials and a grid asset.
- No trained heat model, model metrics, or predictions.
- No waterlogging/flood forecast or susceptibility map.
- No station interpolation, downscaling, or “1 km AQI”.
- No partnership, endorsement, or official status for this platform.

## Adding or replacing a source

1. Add or update a `DataSource` row with real name, provider type, licence,
   attribution, resolution and refresh expectation.
2. Implement the HTTP adapter under `data_pipelines/providers/`.
3. Implement a normaliser under `data_pipelines/normalization/` (or the owning
   app) that preserves source timestamps and units.
4. Write an ingestion service that creates an `IngestionRun` and never writes
   synthetic values on failure.
5. Add API serializers/views that expose state, source and reason.
6. Add deterministic tests for success, partial data, missing fields and
   credential failure.
7. Update this document and `LIMITATIONS.md` if anything remains unverified.
