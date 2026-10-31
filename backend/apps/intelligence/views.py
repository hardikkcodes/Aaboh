from __future__ import annotations

from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.permissions import IsModerator
from apps.core.schemas import DocumentedAPIView
from apps.locations.models import Area, Neighbourhood

from .model_status import build_model_status
from .models import Recommendation, RecommendationEvidence
from .place_status import build_place_status
from .serializers import InsightGenerateRequestSerializer, RecommendationSerializer
from .services import RULESET_VERSION, generate_insights, persist_insights
from .today import build_today, build_week_plan


def _area_from_request(request) -> Area:
    slug = request.query_params.get("area", "kolkata")
    try:
        return Area.objects.get(slug=slug, is_active=True)
    except Area.DoesNotExist as exc:
        raise ValidationError({"area": f"Unknown area: {slug}"}) from exc


def _place_from_request(request, area_slug: str | None = None):
    slug = area_slug or request.query_params.get("area", "kolkata")
    area = Area.objects.filter(slug=slug, is_active=True).first()
    if area is None:
        raise ValidationError({"area": f"Unknown area: {slug}"})

    neighbourhood_slug = request.query_params.get("neighbourhood")
    neighbourhood = None
    if neighbourhood_slug:
        neighbourhood = Neighbourhood.objects.filter(
            area=area, slug=neighbourhood_slug, is_active=True
        ).first()
        if neighbourhood is None:
            raise ValidationError(
                {"neighbourhood": f"Unknown neighbourhood for {area.slug}: {neighbourhood_slug}"}
            )
    return area, neighbourhood


class TodayView(DocumentedAPIView):
    """Personal daily brief for an area or neighbourhood."""

    permission_classes = [AllowAny]

    def get(self, request):
        area, neighbourhood = _place_from_request(request)
        return Response(build_today(area, neighbourhood=neighbourhood))


class ModelStatusView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(build_model_status())


class WeekPlanView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(build_week_plan(_area_from_request(request)))


class PlaceStatusView(DocumentedAPIView):
    """Area-first status for a whole area or one of its neighbourhoods."""

    permission_classes = [AllowAny]

    def get(self, request):
        area, neighbourhood = _place_from_request(request)
        return Response(
            build_place_status(area, neighbourhood=neighbourhood, user=request.user)
        )


class AreaPlaceStatusView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        area, neighbourhood = _place_from_request(request, area_slug=slug)
        return Response(
            build_place_status(area, neighbourhood=neighbourhood, user=request.user)
        )


class InsightsView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        area = _area_from_request(request)
        payload = generate_insights(area)
        rule = request.query_params.get("rule")
        severity = request.query_params.get("severity")
        insights = payload["insights"]
        if rule:
            insights = [item for item in insights if item["rule_id"] == rule]
        if severity:
            insights = [item for item in insights if item["severity"] == severity]
        payload["insights"] = insights
        payload["count"] = len(insights)
        payload["filters"] = {"rule": rule, "severity": severity}
        return Response(payload)


class InsightGenerateView(DocumentedAPIView):
    permission_classes = [IsModerator]

    @extend_schema(request=InsightGenerateRequestSerializer)
    def post(self, request):
        slug = request.data.get("area", "kolkata")
        area = Area.objects.filter(slug=slug, is_active=True).first()
        if area is None:
            raise ValidationError({"area": f"Unknown area: {slug}"})
        payload = generate_insights(area)
        created = persist_insights(area, payload["insights"])
        payload["count"] = len(payload["insights"])
        payload["persisted"] = len(created)
        payload["persisted_ids"] = [str(item.id) for item in created]
        payload["ruleset_version"] = RULESET_VERSION
        return Response(payload)


class InsightHistoryView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        area = _area_from_request(request)
        queryset = (
            Recommendation.objects.filter(area=area)
            .select_related("area")
            .prefetch_related(
                Prefetch("evidence", queryset=RecommendationEvidence.objects.select_related("source"))
            )
            .order_by("-generated_at")
        )
        limit = min(max(int(request.query_params.get("limit", 50)), 1), 200)
        items = list(queryset[:limit])
        return Response(
            {
                "area": {"slug": area.slug, "name": area.name},
                "state": "AVAILABLE" if items else "UNAVAILABLE",
                "count": len(items),
                "results": RecommendationSerializer(items, many=True).data,
                "note": (
                    "Persisted briefings are snapshots generated from the data available at that time."
                ),
            }
        )


class InsightDetailView(DocumentedAPIView):
    permission_classes = [AllowAny]

    @extend_schema(operation_id="insights_detail")
    def get(self, request, pk):
        try:
            recommendation = (
                Recommendation.objects.select_related("area")
                .prefetch_related(
                    Prefetch("evidence", queryset=RecommendationEvidence.objects.select_related("source"))
                )
                .get(pk=pk)
            )
        except Recommendation.DoesNotExist as exc:
            from rest_framework.exceptions import NotFound

            raise NotFound("Insight not found.") from exc
        return Response(RecommendationSerializer(recommendation).data)
