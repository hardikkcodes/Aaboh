from __future__ import annotations

from django.conf import settings

from .models import DataSource


def get_source(slug: str) -> DataSource:
    return DataSource.objects.get(slug=slug)


def provider_configuration() -> dict:
    """Report whether optional providers are configured, without exposing secrets."""
    return {
        "open_meteo": {"configured": settings.OPEN_METEO_ENABLED, "requires_key": False},
        "imd": {"configured": bool(settings.IMD_API_KEY), "requires_key": True},
        "sachet": {"configured": True, "requires_key": False},
        "cpcb": {"configured": bool(settings.CPCB_API_KEY), "requires_key": True},
        "earth_engine": {
            "configured": bool(settings.GEE_PROJECT_ID and settings.GEE_SERVICE_ACCOUNT_EMAIL)
            if hasattr(settings, "GEE_PROJECT_ID")
            else False,
            "requires_key": True,
        },
        "era5_land": {"configured": True, "requires_key": False, "via": "Open-Meteo archive API"},
    }
