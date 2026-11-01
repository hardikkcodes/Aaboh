<div align="center">

# আবহ · Aaboh

**A daily climate companion for Kolkata and the 24 Parganas, in English and Bangla.**

What should I know before I step out? What's happening on my route? How is my neighbourhood changing?

</div>

Aaboh brings rain, heat, air quality, official warnings and live resident reports into one place, in plain language.
It never makes up a value. If data is missing, the app leaves it out or says so.

> **Not an official warning service.** Always follow IMD, KMC and emergency services. In an emergency, call 112.

## Features

| Area | What you get |
| --- | --- |
| **Today** | Rain, feels-like heat, air quality, warnings, the best hours to go out and tips for the day |
| **Live map** | Waterlogging, power cuts, fallen trees and blocked roads reported by residents, with confirmations and expiry |
| **Rain** | Chances counted from 82 forecast runs, by part of day, hour and day, plus a map of low-lying ground |
| **Official warnings** | SACHET warnings matched to your area, with what each one means and what to do |
| **Heat** | Today's risky hours, how your place compares, hottest and coolest areas, and satellite maps |
| **My routes** | Saved trips with reports along the way, rain at your leaving time and rain alerts before you leave |
| **My places** | Save Home or College and use them in search and route planning |
| **Air quality** | Readings from CPCB stations, plus forecast cleanest hours |
| **Climate** | 35 years of local temperature and rain history, explained simply |
| **Neighbourhoods** | A scorecard for ground heat, greenery and low ground, plus report history |
| **Safety** | Emergency numbers, checklists and live cyclone tracking |
| **Open data** | Anonymous reports and map layers to download |

Also included: dark mode, an installable app, sign-up with password reset and email confirmation, and Telegram alerts.

**Areas covered:** Kolkata, North Kolkata, South Kolkata, North 24 Parganas and South 24 Parganas.

## Quick start

You need Python 3.12 or newer, Node 20 or newer, and Git. These commands are for Windows PowerShell. No Docker,
PostgreSQL or GDAL is needed for local development.

**1. Set up**

```powershell
Copy-Item .env.example .env
python -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements\dev.txt
cd frontend; npm install; cd ..
```

**2. Load the places and data**

```powershell
cd backend
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py bootstrap_kolkata
.venv\Scripts\python.exe manage.py bootstrap_regions
.venv\Scripts\python.exe manage.py refresh_data
.venv\Scripts\python.exe manage.py fetch_climate --all-areas
cd ..
```

**3. Run it in two terminals**

```powershell
cd backend; .venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

```powershell
cd frontend; npm run dev
```

Open <http://localhost:5173>. API documentation is at <http://127.0.0.1:8000/api/docs/>.

To use a different backend port, set `$env:VITE_BACKEND_URL` before starting the frontend.

### With Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The frontend runs at <http://localhost:5173> and the API at <http://localhost:8000/api/v1/>.

## Configuration

Copy `.env.example` to `.env`. Never commit `.env`. The app runs without any of these keys, with less data.

| Setting | Turns on | Without it |
| --- | --- | --- |
| `CPCB_API_KEY` | Air quality stations | No station readings |
| `GOOGLE_MAPS_API_KEY` | Google place search and road routes | Local place search and straight-line routes |
| `EMAIL_HOST` and related settings | Real account emails | Emails print to the backend console |
| `TELEGRAM_BOT_TOKEN` | Telegram alerts | In-app notifications only |
| `IMD_API_KEY` | Direct IMD warnings | Warnings come from SACHET, which needs no key |
| `DJANGO_SECRET_KEY`, database settings | Production | Development defaults |

The Google key needs **Places API (New)** and **Routes API** enabled. It stays on the server and never reaches the
browser. Check Google's terms before launch, because Aaboh draws on OpenStreetMap maps.

## Keeping data fresh

In development, the backend refreshes live data in the background while the site is in use. Open pages pick up new
data on their own. To refresh by hand:

```powershell
cd backend; .venv\Scripts\python.exe manage.py refresh_data
```

Production runs `backend/scripts/ingest_loop.sh` instead. Satellite and terrain data are updated by hand, using the
steps in [ml/README.md](ml/README.md).

## Data sources

| Data | Source |
| --- | --- |
| Forecasts and rain chances | Open-Meteo, using ECMWF, GFS and ICON models |
| Official warnings | SACHET, the national alert service run by NDMA |
| Cyclones | GDACS, from the UN and European Commission |
| Air quality | CPCB through data.gov.in, and CAMS forecasts |
| Climate history | ERA5-Land through Open-Meteo |
| Ground heat and greenery | USGS Landsat through Microsoft Planetary Computer |
| Elevation | Copernicus GLO-30 |
| Places and boundaries | OpenStreetMap |
| Street-level reports | Aaboh residents |

## Machine learning

No model changes what residents see today. Each one has to beat a simple baseline on later dates it hasn't seen.

| Model | Result | Status |
| --- | --- | --- |
| Next-day peak temperature | 0.946 °C error, against 1.087 °C for the raw forecast | Passed, not in use |
| Next-day heavy rain | Worse than the forecast alone | Failed, not used |
| Ground heat from satellite data | 1.54 °C error, against 3.08 °C for a same-place, same-month average | Passed, not in use |
| Waterlogging | Terrain and rain inputs are ready | Waiting for 300 real flood reports |

Models are never trained on invented labels. See [ml/README.md](ml/README.md).

## Known limits

- Forecasts come from computer models, not local measurements, and cover wide areas rather than single streets.
- Satellite heat, terrain and scorecards cover Kolkata only.
- North and South Kolkata are split at latitude 22.55. This is an approximation, not an official line.
- The ground map can't see drains, pumps or tides.
- An empty warning list or map doesn't mean conditions are safe.

The full list is in [docs/LIMITATIONS.md](docs/LIMITATIONS.md), and feature status is in
[docs/FEATURE_PRIORITIES.md](docs/FEATURE_PRIORITIES.md).

## Development

| Task | Command |
| --- | --- |
| Backend tests | `cd backend; .venv\Scripts\python.exe -m pytest -q` |
| ML tests | `cd ml; ..\backend\.venv\Scripts\python.exe -m pytest tests -q` |
| Frontend tests | `cd frontend; npm test` |
| Type check | `cd frontend; npm run typecheck` |
| Lint | `cd backend; .venv\Scripts\python.exe -m ruff check .` and `cd frontend; npm run lint` |
| Frontend build | `cd frontend; npm run build` |
| Update the API schema | `cd backend; .venv\Scripts\python.exe manage.py spectacular --file ..\schema.yaml --validate` |

### Project layout

```
backend/         Django API, with one app per area under apps/
data_pipelines/  Adapters for outside data providers
frontend/        React app, built with Vite, TypeScript and Tailwind
ml/              Satellite, terrain and model training code
docs/            Architecture, operations, data and limitations
infra/           PostgreSQL setup
```

**Built with:** React, TypeScript, Vite, Tailwind CSS, TanStack Query, Leaflet, Recharts, Django, Django REST
Framework, SQLite in development, PostgreSQL in production, scikit-learn and XGBoost.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API guide](docs/API.md)
- [Data sources](docs/DATA_SOURCES.md)
- [Data onboarding](docs/DATA_ONBOARDING.md)
- [ML methodology](docs/ML_METHODOLOGY.md)
- [Operations](docs/OPERATIONS.md)
- [Testing](docs/TESTING.md)
- [Decisions](docs/DECISIONS.md)
- [Roadmap](docs/DEVELOPMENT_ROADMAP.md)

## Licence and credits

This repository has no code licence yet. Data stays under each provider's terms:

- Map data © OpenStreetMap contributors, ODbL 1.0
- Weather data by Open-Meteo.com, CC BY 4.0
- ERA5-Land and CAMS from Copernicus
- Landsat from USGS and NASA, public domain
- Elevation from Copernicus GLO-30
- SACHET and CPCB data under Government of India terms
- Cyclone data from GDACS
