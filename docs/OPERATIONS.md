# Operations runbook

This document describes how to install, run, ingest, monitor, back up, and
troubleshoot the platform. It assumes the repository root is the working
directory.

> **Scope.** The current operating mode is a single-node development/demo
> deployment on Windows with SQLite, plus a provisioned PostgreSQL/PostGIS
> Compose stack. It is not yet a hardened public production deployment. See
> [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) Milestone 10 for the gap list.

---

## 1. Prerequisites

| Component | Version used | Notes |
| --- | --- | --- |
| Python | 3.14.7 | 3.12+ should work; ML wheels must exist for your version |
| Node.js | 26.13.0 | 20+; use `npm.cmd` in PowerShell if `npm.ps1` is blocked |
| Git | 2.56 | — |
| Docker | — | Optional; required only for the PostGIS stack |

The development machine used to build this project has **no Docker, PostgreSQL,
PostGIS, or GDAL/GEOS**. SQLite + Shapely/pyproj is the local default (ADR-003).
The Compose path is provided but was not executed here.

---

## 2. Environment variables

Copy the template and edit it:

```powershell
Copy-Item .env.example .env
```

`.env` is gitignored. Never commit real credentials. The application starts
with all optional providers unconfigured and reports `UNAVAILABLE` instead of
fabricating data.

### Core

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME`, `APP_SHORT_NAME`, `APP_TAGLINE` | Civic Climate / CivicClimate / … | Branding returned by `/system/config/` |
| `APP_SUPPORT_EMAIL` | empty | Optional public contact |
| `FRONTEND_URL`, `PUBLIC_SITE_URL` | localhost URLs | Links in metadata and docs |
| `DJANGO_SECRET_KEY` | insecure dev key | **Must** be set for production |
| `DJANGO_DEBUG` | `true` | Set `false` in production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hostnames |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | local Vite origins | Comma-separated origins |
| `DJANGO_LOG_LEVEL` | `INFO` | Root/app log level |
| `DJANGO_LOG_FORMAT` | `plain` | Set `json` for structured logs |

### Database

| Variable | Default | Purpose |
| --- | --- | --- |
| `DB_ENGINE` | `sqlite` | `sqlite` or `postgres` |
| `POSTGRES_DB` | `civic_climate` | Database name |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | `civic` / `change-me` | Change in production |
| `POSTGRES_HOST` / `POSTGRES_PORT` | `localhost` / `5432` | Compose uses `db` |

### Providers

| Variable | Required for | Behaviour when unset |
| --- | --- | --- |
| `OPEN_METEO_ENABLED` | Weather/forecast/archive | Default `true`; no key needed |
| `OPEN_METEO_TIMEOUT_SECONDS` | Open-Meteo calls | Default 30 |
| `IMD_API_KEY` | Official warnings | Alerts `UNAVAILABLE` |
| `IMD_API_KEY_HEADER` | IMD auth header | Default `X-API-Key`; confirm with IMD |
| `IMD_BASE_URL` | IMD endpoint | Default `https://api.imd.gov.in/api/v1` |
| `CPCB_API_KEY` | Station air quality | Air quality `UNAVAILABLE` |
| `CPCB_RESOURCE_ID` | data.gov.in resource | Defaults to the CPCB resource |
| `CPCB_BASE_URL`, `CPCB_TIMEOUT_SECONDS` | CPCB calls | Defaults; timeout 60 s |
| `GEE_PROJECT_ID`, `GEE_SERVICE_ACCOUNT_EMAIL`, `GEE_SERVICE_ACCOUNT_KEY_FILE` | Landsat export | Satellite layers `UNAVAILABLE` |
| `CDS_API_URL`, `CDS_API_KEY` | Direct Copernicus access | Not used; ERA5-Land comes via Open-Meteo |

`/api/v1/system/config/` exposes only booleans (`configured`, `requires_key`),
never secret values.

### Uploads and client

| Variable | Default | Purpose |
| --- | --- | --- |
| `INCIDENT_IMAGE_MAX_BYTES` | `5242880` | Per-image limit (5 MB) |
| `VITE_API_BASE_URL` | `/api/v1` | Frontend API base; build-time for Vite |

> PowerShell can load `.env` manually for commands run outside Django; Django
> itself loads the root `.env`, so management commands pick it up automatically.

---

## 3. First-time local setup

```powershell
# Backend
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements\dev.txt
cd backend
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py bootstrap_kolkata
.venv\Scripts\python.exe manage.py fetch_weather --area kolkata
.venv\Scripts\python.exe manage.py fetch_weather_history --area kolkata --start 2024-10-30
.venv\Scripts\python.exe manage.py fetch_climate --area kolkata --start-year 1991
cd ..

# Frontend
cd frontend
npm.cmd install
cd ..
```

Run two terminals:

```powershell
# Terminal 1
cd backend
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000

# Terminal 2
cd frontend
npm.cmd run dev
```

Open <http://localhost:5173>. The Vite dev server proxies `/api` and `/media` to
`http://127.0.0.1:8000`. If port 8000 is occupied by another process, run Django
on another port and change the proxy target in `frontend/vite.config.ts`.

Create an admin/moderator account:

```powershell
cd backend
.venv\Scripts\python.exe manage.py createsuperuser
```

Set `is_moderator=True` for the account in the Django admin or shell before
using moderation endpoints:

```powershell
.venv\Scripts\python.exe manage.py shell -c "from apps.accounts.models import User; u=User.objects.get(email='you@example.com'); u.is_moderator=True; u.save()"
```

---

## 4. Ingestion

All ingestion is explicit and idempotent (ADR-012). Commands update existing
natural keys rather than duplicating rows.

| Command | Cadence | Depends on |
| --- | --- | --- |
| `bootstrap_kolkata` | Once, or when geography changes | Network (OSM) |
| `fetch_weather` | Every 1–3 hours | Open-Meteo; no key |
| `fetch_weather_history` | Daily (incremental window) | Open-Meteo archive |
| `fetch_climate` | Monthly/seasonal | Open-Meteo archive |
| `fetch_alerts` | Every 15–30 minutes | `IMD_API_KEY` |
| `fetch_cpcb` | Hourly | `CPCB_API_KEY` |
| `ingest_landsat_observations` | Per successful satellite export | GEE + grid asset |
| `register_heat_model` | Per evaluated training run | ML artifact |
| `ingest_heat_predictions` | Per prediction run | Registered model |

Commands:

```powershell
cd backend
.venv\Scripts\python.exe manage.py bootstrap_kolkata [--skip-grid] [--skip-localities]
.venv\Scripts\python.exe manage.py fetch_weather --area kolkata --forecast-days 7
.venv\Scripts\python.exe manage.py fetch_weather_history --area kolkata --start 2024-10-30 --end 2026-10-29
.venv\Scripts\python.exe manage.py fetch_climate --area kolkata --start-year 1991 --baseline-start 1991 --baseline-end 2020
.venv\Scripts\python.exe manage.py fetch_alerts
.venv\Scripts\python.exe manage.py fetch_cpcb
.venv\Scripts\python.exe manage.py ingest_landsat_observations --dataset export.csv --min-valid-fraction 0.5
.venv\Scripts\python.exe manage.py register_heat_model --artifact artifacts/heat-YYYYMMDD [--activate]
.venv\Scripts\python.exe manage.py ingest_heat_predictions --predictions predictions.csv [--model-version v1]
```

### Scheduling

`docker-compose.prod.yml` includes a `scheduler` service that runs
`backend/scripts/ingest_loop.sh`. Local runs have no scheduler, so use Windows
Task Scheduler or cron if you need fresh data there. A practical minimum:

- weather current/forecast: every 3 hours (freshness threshold is 3 hours);
- community expiry/moderation: daily review;
- archive history/climate: daily and monthly respectively;
- alerts/CPCB: only after credentials are configured.

Log the exit code and stdout of each run. A failed ingestion leaves the previous
data in place and `/system/data-status/` will show it as `STALE`, not silently
fresh.

### Backfill caveats

- Weather history is capped at 730 days per request in the API; the ingestion
  command accepts explicit start/end dates.
- Climate fetch is slow because it requests long archive windows; run it during
  off-hours.
- Re-running bootstrap with a different grid version creates a new grid; it does
  not mutate the existing one.

---

## 5. Health and monitoring

| Endpoint | Use |
| --- | --- |
| `GET /api/v1/health/` | Liveness; includes database status and spatial engine |
| `GET /api/v1/health/ready/` | Readiness; 503 if the database is unusable |
| `GET /api/v1/system/data-status/` | Per-module state, last success, reasons |
| `GET /api/v1/system/config/` | Provider configuration booleans |

Monitor at least:

- health/readiness every minute;
- data-status after every ingestion run;
- provider error rate and ingestion duration in logs;
- disk usage for `backend/media/` and the database.

Logs are written to stdout as plain text by default. Set
`DJANGO_LOG_FORMAT=json` for machine parsing. Docker Compose: `docker compose
logs -f backend`.

### What "stale" means

- weather current/forecast: last successful retrieval older than 3 hours;
- provider modules with stored rows but a failed recent refresh: response state
  becomes `STALE` and `reason` explains the failure;
- satellite/climate data: freshness is shown per layer/metric with the
  observation date, not only retrieval time.

---

## 6. Docker Compose deployment

```powershell
Copy-Item .env.example .env
# Edit .env: DB_ENGINE=postgres, strong passwords, DJANGO_DEBUG=false, secrets
docker compose up --build
```

Topology:

- `db`: `postgis/postgis:16-3.4`, persistent `postgres_data` volume, init SQL.
- `backend`: Django on `:8000`, waits for the database healthcheck, runs
  migrations and Kolkata bootstrap on start, mounts `media_data`.
- `frontend`: multi-stage Node build served by Nginx on host `:5173`
  (container `:80`), proxying `/api/`, `/admin/`, and `/static/` to
  `backend:8000` and serving `/media/` from a read-only shared volume.

### Production stack

`docker-compose.yml` is for local use: it runs `runserver` and mounts the source.
For public use, set these in `.env`:

- `DJANGO_SECRET_KEY`: a random value of at least 50 characters
- `POSTGRES_PASSWORD`: a strong password
- `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `DJANGO_CSRF_TRUSTED_ORIGINS`:
  your real domain
- `DJANGO_NUM_PROXIES`: `2` behind nginx plus a hosting TLS proxy (the default),
  or `1` if nginx is directly public

```powershell
docker compose -f docker-compose.prod.yml up -d --build
```

This runs Gunicorn as a non-root user, keeps Postgres off the host network, and
starts the ingestion scheduler. TLS must be terminated in front of the frontend
port. Django refuses to start with `DJANGO_DEBUG=false` and a weak secret.

Notes and caveats:

- The frontend API base URL is baked at build time. Changing it requires a
  rebuild.
- The bootstrap runs on every container start; it is idempotent but needs
  network access to OSM. Use a flag or a separate init job if the network is
  restricted.
- Native PostGIS is provisioned but the application models still use GeoJSON
  fields until ADR-003 is revisited.

Stop and remove (data volumes are preserved unless `-v`):

```powershell
docker compose down
docker compose down -v   # destructive: deletes database and media volumes
```

---

## 7. Backup and restore

### SQLite (current development mode)

The database is `backend/db.sqlite3`. Stop the server, copy the file, and copy
`backend/media/` for report images:

```powershell
Copy-Item backend\db.sqlite3 backups\db-$(Get-Date -Format yyyyMMdd-HHmm).sqlite3
Copy-Item backend\media backups\media-$(Get-Date -Format yyyyMMdd-HHmm) -Recurse
```

Restore by replacing the file while the server is stopped. Never copy a SQLite
file while a write transaction is in progress.

### PostgreSQL

```powershell
docker compose exec db pg_dump -U civic -Fc civic_climate > backup.dump
docker compose exec -T db pg_restore -U civic -d civic_climate < backup.dump
```

Back up the media volume separately (`docker run --rm -v civic-climate_media_data:/data ...`
or a volume snapshot). Test a restore into a scratch database before relying on
the backup.

---

## 8. Security checklist

Before exposing the service publicly:

- [ ] `DJANGO_DEBUG=false`, strong `DJANGO_SECRET_KEY`, non-default DB password.
- [ ] HTTPS at the proxy; secure cookies; HSTS.
- [ ] Restrict `DJANGO_ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` to real hosts.
- [ ] Serve through Gunicorn/Uvicorn, not `runserver`.
- [ ] Put rate limiting at the edge in addition to DRF throttles.
- [ ] Keep media uploads out of executable paths; the app already validates,
      re-encodes, and strips EXIF, but scan uploads if the threat model requires.
- [ ] Review moderator accounts and remove stale ones.
- [ ] Set up database and media backups with a tested restore.
- [ ] Publish a privacy/retention policy for community reports and images.
- [ ] Add account deletion/data export before collecting real user data.
- [ ] Do not expose the Django admin without additional protection.

---

## 9. Troubleshooting

| Symptom | Likely cause | Action |
| --- | --- | --- |
| Alert/AQ/satellite/heat page empty | Missing credential or dataset | Check `/system/data-status/`; set the documented key; re-run the command |
| Weather page shows `STALE` | No recent `fetch_weather` | Run it; check network/proxy; inspect command output |
| All API calls 404 | Wrong host/port or missing `/api/v1/` prefix | Confirm the backend port and base path |
| Frontend calls fail in dev | Vite proxy target wrong / backend down | Start Django on the configured port; check `vite.config.ts` |
| `npm` blocked in PowerShell | Execution policy blocks `npm.ps1` | Use `npm.cmd` |
| `manage.py` import errors | Run from wrong directory or wrong interpreter | Use `backend\.venv\Scripts\python.exe` and run inside `backend/` |
| Map tiles missing | No network access to OSM | Tiles require network; data layers still render without basemap |
| Report upload rejected | Type/size/EXIF or count limit | Check `INCIDENT_IMAGE_MAX_BYTES`, accepted image types, ≤ 4 files |
| Report location rejected | Point outside the area boundary | Choose a point inside Kolkata; check the polygon source |
| `429` on login/register | Auth throttle (10/min) | Wait; do not loop retries |
| `429` on report creation | 12/hour per user | Wait; review for accidental duplicates |
| SQLite "database is locked" | Long write or concurrent ingestion | Retry after the writer finishes; consider PostgreSQL for concurrency |
| GEE export exits without output | Missing project/service account/grid asset | Set all three GEE variables and register the grid asset |
| Model registration refused | Artifact missing metrics/manifest or too small | Re-train with the required rows/dates; read the error |

### Useful checks

```powershell
cd backend
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe showmigrations
.venv\Scripts\python.exe shell -c "from apps.locations.models import Area, GridCell; print(Area.objects.count(), GridCell.objects.count())"
```

If the database is empty, re-run `bootstrap_kolkata`, `fetch_weather`, and
`fetch_climate`. The application will not invent data to fill the gap.

---

## 10. Incident response

1. Confirm the scope with `/health/` and `/system/data-status/`.
2. If a provider is down or a credential is invalid, leave the last good data in
   place; the API will mark it stale. Do not manually insert replacement values.
3. If community content is abusive or unsafe, hide/moderate it through the
   moderation endpoint and preserve the audit history.
4. If the database is corrupted, restore the most recent backup and replay
   ingestion commands. Community reports created after the backup are lost;
   record the gap in the incident log.
5. Rotate any exposed credential immediately and restart the backend.
