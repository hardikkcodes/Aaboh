from __future__ import annotations

from django.db.models import Prefetch
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsModerator
from apps.locations.models import Area

from .models import Recommendation, RecommendationEvidence
from .serializers import RecommendationSerializer
from .services import RULESET_VERSION, generate_insights, persist_insights


def _area_from_request(request) -> Area:
    slug = request.query_params.get("area", "kolkata")
    try:
        return Area.objects.get(slug=slug, is_active=True)
    except Area.DoesNotExist as exc:
        raise ValidationError({"area": f"Unknown area: {slug}"}) from exc


class InsightsView(APIView):
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


class InsightGenerateView(APIView):
    permission_classes = [IsModerator]

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


class InsightHistoryView(APIView):
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


class InsightDetailView(APIView):
    permission_classes = [AllowAny]

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
