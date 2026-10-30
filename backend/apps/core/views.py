from __future__ import annotations

from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import __version__
from .models import DataSource
from .quality import source_availability
from .sources import provider_configuration

PUBLIC_MODULES = {
    "weather": "open_meteo",
    "alerts": "imd",
    "air_quality": "cpcb",
    "environment": "landsat",
    "climate": "era5_land",
    "community": "community_reports",
}

MODULE_REASONS = {
    "weather": "No weather forecast has been ingested. Run fetch_weather.",
    "alerts": "IMD_API_KEY is not configured, so the official warning feed is unavailable.",
    "air_quality": "CPCB_API_KEY is not configured, so station measurements are unavailable.",
    "environment": "No satellite observations have been ingested. Google Earth Engine credentials may be missing.",
    "climate": "No ERA5-Land climate metrics have been ingested. Run fetch_climate.",
    "community": "No public community reports have been submitted yet.",
}


def _database_check() -> tuple[bool, str]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True, "ok"
    except Exception:  # noqa: BLE001 - health checks must never raise
        return False, "unavailable"


class HealthView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        db_ok, db_state = _database_check()
        payload = {
            "status": "ok" if db_ok else "degraded",
            "version": __version__,
            "checks": {
                "database": db_state,
                "spatial_engine": "shapely (portable GeoJSON mode)",
            },
        }
        return Response(payload, status=status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE)


class ReadinessView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        db_ok, _ = _database_check()
        try:
            from apps.locations.models import Area

            areas = Area.objects.count()
            ready = db_ok and areas > 0
            reason = None if ready else ("database_unavailable" if not db_ok else "geography_not_bootstrapped")
        except Exception:  # noqa: BLE001
            ready, reason = False, "schema_not_migrated"
        return Response(
            {"ready": ready, "reason": reason},
            status=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class SystemConfigView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "branding": {
                    "name": settings.APP_CONFIG["name"],
                    "short_name": settings.APP_CONFIG["short_name"],
                    "tagline": settings.APP_CONFIG["tagline"],
                    "support_email": settings.APP_CONFIG["support_email"],
                },
                "default_city": settings.APP_CONFIG["default_city"],
                "timezone": settings.APP_CONFIG["timezone"],
                "providers": provider_configuration(),
            }
        )


class DataStatusView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request):
        sources = {source.slug: source for source in DataSource.objects.filter(is_active=True)}
        modules = {}
        for module, slug in PUBLIC_MODULES.items():
            source = sources.get(slug)
            if source is None:
                modules[module] = {"state": "UNAVAILABLE", "source": None, "reason": "source_not_registered"}
                continue
            availability = source_availability(source)
            state = availability["state"]
            reason = None if state in {"AVAILABLE", "PARTIAL", "PROCESSING"} else MODULE_REASONS.get(module)
            modules[module] = {
                "state": state,
                "source": {
                    "slug": source.slug,
                    "name": source.name,
                    "provider_type": source.provider_type,
                    "is_official": source.is_official,
                },
                "last_success_at": availability.get("last_success_at"),
                "reason": reason,
            }

        try:
            from apps.incidents.models import IncidentReport

            public_reports = IncidentReport.objects.filter(is_public=True).count()
        except Exception:  # noqa: BLE001 - status endpoint must degrade, not fail
            public_reports = 0
        if public_reports:
            modules["community"]["state"] = "AVAILABLE"
            modules["community"]["reason"] = None
        else:
            modules["community"]["state"] = "UNAVAILABLE"
            modules["community"]["reason"] = MODULE_REASONS["community"]

        return Response(
            {
                "generated_at": timezone.now(),
                "providers": provider_configuration(),
                "modules": modules,
                "sources": [
                    {
                        "slug": source.slug,
                        "name": source.name,
                        "provider_type": source.provider_type,
                        "is_official": source.is_official,
                        "spatial_resolution_m": source.spatial_resolution_m,
                        "attribution": source.attribution,
                        **source_availability(source),
                    }
                    for source in sources.values()
                ],
            }
        )
