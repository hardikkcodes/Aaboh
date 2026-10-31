from __future__ import annotations

from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.schemas import DocumentedAPIView
from apps.environment.models import EnvironmentalObservation
from apps.locations.models import Area

from .models import CellPrediction, ModelVersion, PredictionRun, PredictionRunStatus
from .serializers import CellPredictionSerializer, ModelVersionSerializer, PredictionRunSerializer


def _area(request) -> Area | None:
    slug = request.query_params.get("area", "kolkata")
    area = Area.objects.filter(slug=slug, is_active=True).first()
    return area.data_area if area else None


def _nearest_place(cell, places) -> str:
    nearest = min(
        places,
        key=lambda place: (place.latitude - cell.centroid_lat) ** 2 + (place.longitude - cell.centroid_lon) ** 2,
        default=None,
    )
    return nearest.name if nearest else cell.code


class HeatPredictionsView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        area = _area(request)
        if area is None:
            return Response(
                {"error": {"code": "not_found", "message": "Area not found.", "details": None}},
                status=404,
            )
        run = (
            PredictionRun.objects.filter(area=area, status=PredictionRunStatus.COMPLETE)
            .select_related("model_version")
            .order_by("-generated_at")
            .first()
        )
        if run is None:
            active = ModelVersion.objects.filter(task="lst_estimation", is_operational=True).first()
            reason = "No completed prediction run exists for this area, so no estimates are shown."
            if active:
                reason = "A model is registered but no completed prediction run exists for this area."
            return Response(
                {
                    "area": {"slug": area.slug, "name": area.name},
                    "state": "UNAVAILABLE",
                    "run": None,
                    "results": [],
                    "reason": reason,
                    "disclaimer": "Estimated LST is not measured air temperature.",
                }
            )
        predictions = CellPrediction.objects.filter(run=run).select_related("cell")
        return Response(
            {
                "area": {"slug": area.slug, "name": area.name},
                "state": "AVAILABLE",
                "run": PredictionRunSerializer(run).data,
                "count": predictions.count(),
                "results": CellPredictionSerializer(predictions, many=True).data,
                "disclaimer": (
                    "Predicted land-surface temperature is a model estimate, not an air-temperature "
                    "measurement or an official heat warning."
                ),
            }
        )


class HeatHotspotsView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        area = _area(request)
        if area is None:
            return Response(
                {"error": {"code": "not_found", "message": "Area not found.", "details": None}},
                status=404,
            )
        base = EnvironmentalObservation.objects.filter(cell__area=area, lst_c__isnull=False)
        latest_date = base.order_by("-observed_on").values_list("observed_on", flat=True).first()
        if latest_date is None:
            return Response(
                {
                    "area": {"slug": area.slug, "name": area.name},
                    "state": "UNAVAILABLE",
                    "date": None,
                    "threshold_c": None,
                    "count": 0,
                    "results": [],
                    "reason": "Satellite heat maps cover Kolkata for now. No observations are stored for this area.",
                }
            )
        observations = list(
            base.filter(observed_on=latest_date).select_related("cell", "scene").order_by("-lst_c")
        )
        values = sorted(obs.lst_c for obs in observations)
        places = list(area.neighbourhoods.filter(is_active=True))
        if not values:
            threshold = None
            hotspots = []
        else:
            index = min(len(values) - 1, max(0, int(round(0.9 * (len(values) - 1)))))
            threshold = values[index]
            hotspots = [obs for obs in observations if obs.lst_c >= threshold]
        return Response(
            {
                "area": {"slug": area.slug, "name": area.name},
                "state": "AVAILABLE",
                "date": latest_date,
                "threshold_c": round(threshold, 2) if threshold is not None else None,
                "count": len(hotspots),
                "results": [
                    {
                        "cell_code": obs.cell.code,
                        "place": _nearest_place(obs.cell, places),
                        "geometry": obs.cell.geometry,
                        "centroid": obs.cell.centroid,
                        "lst_c": obs.lst_c,
                        "valid_pixel_fraction": obs.valid_pixel_fraction,
                        "scene_id": obs.scene.scene_id,
                    }
                    for obs in hotspots[:200]
                ],
                "method": (
                    "Cells at or above the 90th percentile of observed LST for the latest scene date. "
                    "This is a descriptive hotspot analysis, not an ML prediction."
                ),
            }
        )


class HeatModelInfoView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        versions = ModelVersion.objects.filter(task="lst_estimation").order_by("-created_at")
        active = versions.filter(is_active=True).first()
        return Response(
            {
                "state": "AVAILABLE" if versions.exists() else "UNAVAILABLE",
                "active_model": ModelVersionSerializer(active).data if active else None,
                "versions": ModelVersionSerializer(versions, many=True).data,
                "target": "predicted_lst_c",
                "note": (
                    "Model metrics are only shown when produced by a reproducible evaluation run. "
                    "LST estimates are land-surface temperature, never air temperature."
                ),
                "reason": None
                if versions.exists()
                else (
                    "No evaluated heat model has been registered. The training pipeline requires labelled "
                    "satellite observations; see docs/ML_METHODOLOGY.md."
                ),
            }
        )
