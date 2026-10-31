from __future__ import annotations

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.models import DataSource
from apps.core.quality import source_availability
from apps.core.schemas import DocumentedAPIView
from apps.core.serializers import source_summary
from apps.locations.models import Area, GridCell

from .models import CellTerrain, EnvironmentalObservation
from .serializers import EnvironmentalObservationSerializer

LAYER_DEFINITIONS = {
    "lst_c": {
        "label": "Land surface temperature",
        "unit": "°C",
        "description": "Thermal-band land-surface temperature aggregated to 1 km cells. Not air temperature.",
        "native_resolution": "Landsat thermal: 100 m, resampled to 30 m in Collection 2 Level 2",
    },
    "ndvi": {
        "label": "NDVI (vegetation)",
        "unit": "index",
        "description": "Normalised difference vegetation index from surface-reflectance bands.",
        "native_resolution": "30 m",
    },
    "ndbi": {
        "label": "NDBI (built-up)",
        "unit": "index",
        "description": "Normalised difference built-up index from surface-reflectance bands.",
        "native_resolution": "30 m",
    },
    "mndwi": {
        "label": "MNDWI (water)",
        "unit": "index",
        "description": "Modified normalised difference water index from surface-reflectance bands.",
        "native_resolution": "30 m",
    },
}


def _satellite_source():
    return DataSource.objects.filter(slug="landsat").first()


def _gee_configured() -> bool:
    return bool(
        getattr(settings, "GEE_PROJECT_ID", "")
        and getattr(settings, "GEE_SERVICE_ACCOUNT_EMAIL", "")
    )


class EnvironmentLayersView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        source = _satellite_source()
        availability = source_availability(source) if source else {"state": "UNAVAILABLE", "last_success_at": None}
        observations = EnvironmentalObservation.objects.all()
        latest = observations.order_by("-observed_on").first()
        available_variables: set[str] = set()
        for variable in LAYER_DEFINITIONS:
            if observations.exclude(**{f"{variable}__isnull": True}).exists():
                available_variables.add(variable)
        has_data = bool(latest)
        state = "AVAILABLE" if has_data else "UNAVAILABLE"
        return Response(
            {
                "state": state,
                "source": source_summary(source) if source else {},
                "last_success_at": availability.get("last_success_at"),
                "latest_observation_date": latest.observed_on if latest else None,
                "layers": [
                    {
                        "key": key,
                        **definition,
                        "available": key in available_variables,
                        "latest_date": latest.observed_on if latest and key in available_variables else None,
                    }
                    for key, definition in LAYER_DEFINITIONS.items()
                ],
                "cell_size_m": 1000,
                "note": (
                    "The 1 km grid is an analytical aggregation unit. Satellite indices retain their "
                    "native resolution and are not independent 1 km measurements."
                ),
                "reason": None
                if has_data
                else (
                    "No satellite observations have been ingested. "
                    + ("" if _gee_configured() else "Google Earth Engine credentials are not configured.")
                ).strip(),
            }
        )


class EnvironmentObservationsView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        variable = request.query_params.get("variable", "lst_c")
        if variable not in LAYER_DEFINITIONS:
            return Response(
                {
                    "error": {
                        "code": "invalid_variable",
                        "message": f"Unknown variable. Choose one of: {', '.join(LAYER_DEFINITIONS)}",
                        "details": None,
                    }
                },
                status=400,
            )
        queryset = EnvironmentalObservation.objects.select_related("cell", "scene").exclude(
            **{f"{variable}__isnull": True}
        )
        observed_on = request.query_params.get("date")
        if observed_on:
            queryset = queryset.filter(observed_on=observed_on)
        else:
            latest_date = queryset.order_by("-observed_on").values_list("observed_on", flat=True).first()
            if latest_date:
                queryset = queryset.filter(observed_on=latest_date)
        queryset = queryset.order_by("cell__row", "cell__col")[:2000]

        features = [
            {
                "type": "Feature",
                "geometry": obs.cell.geometry,
                "properties": {
                    "cell_code": obs.cell.code,
                    "value": getattr(obs, variable),
                    "variable": variable,
                    "unit": LAYER_DEFINITIONS[variable]["unit"],
                    "observed_on": obs.observed_on,
                    "scene_id": obs.scene.scene_id,
                    "valid_pixel_fraction": obs.valid_pixel_fraction,
                    "quality_flags": obs.quality_flags,
                },
            }
            for obs in queryset
        ]
        return Response(
            {
                "type": "FeatureCollection",
                "state": "AVAILABLE" if features else "UNAVAILABLE",
                "variable": variable,
                "count": len(features),
                "features": features,
                "note": (
                    "Cell values are aggregations of satellite pixels; they do not imply 1 km native "
                    "measurement resolution."
                ),
            }
        )


class EnvironmentTerrainView(DocumentedAPIView):
    """Low-lying ground by grid cell. Shows where water could gather, not where it will."""

    permission_classes = [AllowAny]

    def get(self, request):
        area = Area.objects.filter(slug=request.query_params.get("area", "kolkata"), is_active=True).first()
        terrain = (
            CellTerrain.objects.filter(cell__area=area.data_area).select_related("cell") if area else []
        )
        features = [
            {
                "type": "Feature",
                "geometry": item.cell.geometry,
                "properties": {
                    "cell_code": item.cell.code,
                    "susceptibility": item.susceptibility,
                    "terrain_class": item.terrain_class,
                    "elevation_m": item.elevation_m,
                    "relative_elevation_m": item.relative_elevation_m,
                },
            }
            for item in terrain
        ]
        return Response(
            {
                "type": "FeatureCollection",
                "state": "AVAILABLE" if features else "UNAVAILABLE",
                "count": len(features),
                "features": features,
                "source": terrain[0].dem_source if features else None,
            }
        )


class EnvironmentCellDetailView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request, cell_code):
        cell = get_object_or_404(GridCell.objects.select_related("area", "definition"), code=cell_code)
        observations = cell.observations.select_related("scene").order_by("-observed_on")[:60]
        return Response(
            {
                "cell": {
                    "code": cell.code,
                    "area": cell.area.slug,
                    "grid_version": cell.definition.version,
                    "row": cell.row,
                    "col": cell.col,
                    "geometry": cell.geometry,
                    "centroid": cell.centroid,
                    "coverage_fraction": cell.coverage_fraction,
                    "area_km2": cell.area_km2,
                },
                "state": "AVAILABLE" if observations else "UNAVAILABLE",
                "observations": EnvironmentalObservationSerializer(observations, many=True).data,
                "note": "LST is land-surface temperature, not measured air temperature.",
            }
        )
