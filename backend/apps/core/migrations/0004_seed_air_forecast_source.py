"""Register the CAMS air-quality forecast. Only source metadata is seeded here."""

from django.db import migrations

SOURCE = {
    "slug": "cams_air",
    "name": "CAMS air-quality forecast (via Open-Meteo)",
    "provider_type": "forecast_model",
    "description": "Copernicus Atmosphere Monitoring Service modelled PM2.5 and PM10 forecasts.",
    "homepage_url": "https://open-meteo.com/en/docs/air-quality-api",
    "license_name": "CC BY 4.0",
    "license_url": "https://open-meteo.com/en/license",
    "attribution": "Copernicus Atmosphere Monitoring Service via Open-Meteo",
    "spatial_resolution_m": 40000,
    "temporal_resolution": "hourly",
    "expected_refresh_minutes": 360,
    "metadata": {"requires_key": False},
}


def seed(apps, schema_editor):
    DataSource = apps.get_model("core", "DataSource")
    defaults = {key: value for key, value in SOURCE.items() if key != "slug"}
    DataSource.objects.update_or_create(slug=SOURCE["slug"], defaults=defaults)


def unseed(apps, schema_editor):
    apps.get_model("core", "DataSource").objects.filter(slug=SOURCE["slug"]).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0003_seed_sachet_source")]

    operations = [migrations.RunPython(seed, unseed)]
