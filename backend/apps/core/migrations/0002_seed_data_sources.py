"""Register the provenance records every ingestion command depends on.

This migration deliberately contains no environmental observations, stations,
alerts or metrics. Only descriptions of real data sources are seeded.
"""

from django.db import migrations

SOURCES = [
    {
        "slug": "osm",
        "name": "OpenStreetMap contributors",
        "provider_type": "supplementary",
        "description": (
            "Community-maintained map data used for the Kolkata administrative boundary and "
            "named locality points. Not an official KMC boundary or ward map."
        ),
        "homepage_url": "https://www.openstreetmap.org/",
        "license_name": "Open Data Commons Open Database License (ODbL) 1.0",
        "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "attribution": "© OpenStreetMap contributors",
        "spatial_resolution_m": None,
        "temporal_resolution": "continuous, community-maintained",
        "expected_refresh_minutes": None,
        "metadata": {
            "boundary_ref": "OSM relation 9381363",
            "boundary_admin_level": 8,
            "wikidata": "Q1348",
            "caveat": "Community-maintained boundary; replace with an official KMC dataset when available.",
        },
    },
    {
        "slug": "open_meteo",
        "name": "Open-Meteo",
        "provider_type": "forecast_model",
        "description": (
            "Weather forecast and historical archive API. Forecast values are model output, not "
            "official station observations or warnings."
        ),
        "homepage_url": "https://open-meteo.com/",
        "license_name": "Creative Commons Attribution 4.0 (CC BY 4.0)",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "Weather data by Open-Meteo.com",
        "spatial_resolution_m": None,
        "temporal_resolution": "hourly forecast; daily archive",
        "expected_refresh_minutes": 180,
        "metadata": {
            "requires_key": False,
            "resolution_note": (
                "Open-Meteo selects the best available model for the requested point; native grid "
                "spacing varies by variable and model, so no single resolution is asserted here."
            ),
        },
    },
    {
        "slug": "imd",
        "name": "India Meteorological Department",
        "provider_type": "official",
        "description": (
            "Official weather warnings published by IMD. The public API requires a key; without "
            "credentials this platform reports the feed as unavailable."
        ),
        "homepage_url": "https://mausam.imd.gov.in/",
        "license_name": "Government of India — IMD terms of use",
        "license_url": "",
        "attribution": "India Meteorological Department",
        "spatial_resolution_m": None,
        "temporal_resolution": "event-driven warnings",
        "expected_refresh_minutes": 30,
        "metadata": {
            "requires_key": True,
            "credential_variable": "IMD_API_KEY",
            "header_confirmation": "The API key header name must be confirmed with IMD; configurable via IMD_API_KEY_HEADER.",
        },
    },
    {
        "slug": "cpcb",
        "name": "Central Pollution Control Board (data.gov.in)",
        "provider_type": "official",
        "description": (
            "Station-based air-quality measurements published through data.gov.in. Values are "
            "station-specific and are never interpolated into a neighbourhood surface."
        ),
        "homepage_url": "https://cpcb.nic.in/",
        "license_name": "Government Open Data License — India",
        "license_url": "https://data.gov.in/government-open-data-license-india",
        "attribution": "Central Pollution Control Board / data.gov.in",
        "spatial_resolution_m": None,
        "temporal_resolution": "station reports, typically hourly",
        "expected_refresh_minutes": 60,
        "metadata": {
            "requires_key": True,
            "credential_variable": "CPCB_API_KEY",
            "resource_id": "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69",
        },
    },
    {
        "slug": "landsat",
        "name": "USGS Landsat Collection 2",
        "provider_type": "earth_observation",
        "description": (
            "Landsat surface-reflectance and thermal imagery used for land-surface temperature, "
            "NDVI, NDBI and MNDWI. Processing requires Google Earth Engine credentials."
        ),
        "homepage_url": "https://www.usgs.gov/landsat-missions",
        "license_name": "Public domain (USGS)",
        "license_url": "https://www.usgs.gov/legal",
        "attribution": "USGS/NASA Landsat",
        "spatial_resolution_m": 30,
        "temporal_resolution": "16-day revisit (Landsat 8/9, combined)",
        "expected_refresh_minutes": 23040,
        "metadata": {
            "requires_key": True,
            "credential_variables": ["GEE_PROJECT_ID", "GEE_SERVICE_ACCOUNT_EMAIL", "GEE_SERVICE_ACCOUNT_KEY_FILE"],
            "thermal_resolution_m": 100,
            "collection": "LANDSAT/LC08/C02/T1_L2 and LANDSAT/LC09/C02/T1_L2",
        },
    },
    {
        "slug": "era5_land",
        "name": "ERA5-Land via Open-Meteo archive",
        "provider_type": "reanalysis",
        "description": (
            "ERA5-Land reanalysis daily aggregates accessed through the Open-Meteo archive API. "
            "Native resolution is approximately 9 km; metrics are area-level, not local observations."
        ),
        "homepage_url": "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land",
        "license_name": "Copernicus Climate Change Service licence",
        "license_url": "https://cds.climate.copernicus.eu/licence",
        "attribution": "ERA5-Land / Copernicus Climate Change Service",
        "spatial_resolution_m": 9000,
        "temporal_resolution": "daily aggregates",
        "expected_refresh_minutes": 1440,
        "metadata": {
            "requires_key": False,
            "access_path": "Open-Meteo archive API (no CDS key required)",
            "direct_cds_adapter": "not implemented",
        },
    },
    {
        "slug": "community_reports",
        "name": "Civic Climate community reports",
        "provider_type": "community",
        "description": (
            "Environmental incidents submitted by authenticated residents. Reports are unverified "
            "until a moderator changes their status and are never treated as official alerts."
        ),
        "homepage_url": "",
        "license_name": "Platform contribution terms",
        "license_url": "",
        "attribution": "Community contributors",
        "spatial_resolution_m": None,
        "temporal_resolution": "event-driven submissions",
        "expected_refresh_minutes": None,
        "metadata": {
            "moderation_required": True,
            "public_identity_policy": "Reporter email and identity are never exposed publicly.",
        },
    },
    {
        "slug": "development_fixture",
        "name": "Development fixture",
        "provider_type": "development_fixture",
        "description": (
            "Reserved provenance marker for synthetic records created only in automated tests. "
            "Production and development databases must not contain synthetic environmental data."
        ),
        "homepage_url": "",
        "license_name": "Not for production use",
        "license_url": "",
        "attribution": "",
        "spatial_resolution_m": None,
        "temporal_resolution": "",
        "expected_refresh_minutes": None,
        "metadata": {"synthetic": True, "test_only": True},
    },
]


def seed_sources(apps, schema_editor):
    DataSource = apps.get_model("core", "DataSource")
    for payload in SOURCES:
        slug = payload["slug"]
        defaults = {key: value for key, value in payload.items() if key != "slug"}
        DataSource.objects.update_or_create(slug=slug, defaults=defaults)


def unseed_sources(apps, schema_editor):
    DataSource = apps.get_model("core", "DataSource")
    DataSource.objects.filter(slug__in=[item["slug"] for item in SOURCES]).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [migrations.RunPython(seed_sources, unseed_sources)]
