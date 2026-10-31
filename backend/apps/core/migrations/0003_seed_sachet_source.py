"""Register SACHET as an official, key-free alert source.

SACHET (NDMA) is added alongside the existing IMD source: IMD stays the
preferred feed when credentials exist, and SACHET is the public alternative that
works without a key. Only source metadata is seeded here.
"""

from django.db import migrations

SACHET = {
    "slug": "sachet",
    "name": "SACHET - NDMA alert platform",
    "provider_type": "official",
    "description": (
        "Official CAP-style alerts issued by State Disaster Management Authorities and central "
        "agencies (IMD, CWC), published nationally by the National Disaster Management Authority's "
        "SACHET platform. The feed is national, publishes area text and a centroid but no polygon, "
        "and is filtered to the configured Kolkata scope."
    ),
    "homepage_url": "https://sachet.ndma.gov.in/",
    "license_name": "Government of India - NDMA public alert feed",
    "license_url": "https://sachet.ndma.gov.in/",
    "attribution": "National Disaster Management Authority (SACHET)",
    "spatial_resolution_m": None,
    "temporal_resolution": "event-driven alerts with effective/expiry times",
    "expected_refresh_minutes": 15,
    "metadata": {
        "requires_key": False,
        "scope_matching": "Published area_description text; the feed has no polygon.",
        "imd_relationship": (
            "IMD alerts are distributed through this platform when IMD is the issuing agency. "
            "The source label on each alert names the actual issuing agency."
        ),
    },
}


def seed_sachet(apps, schema_editor):
    DataSource = apps.get_model("core", "DataSource")
    defaults = {key: value for key, value in SACHET.items() if key != "slug"}
    DataSource.objects.update_or_create(slug=SACHET["slug"], defaults=defaults)


def unseed_sachet(apps, schema_editor):
    DataSource = apps.get_model("core", "DataSource")
    DataSource.objects.filter(slug=SACHET["slug"]).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0002_seed_data_sources")]

    operations = [migrations.RunPython(seed_sachet, unseed_sachet)]
