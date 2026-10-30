from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import DataSource
from apps.core.quality import source_availability
from apps.core.serializers import source_summary

from .models import AlertStatus, OfficialAlert
from .serializers import OfficialAlertSerializer


class AlertListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        source = DataSource.objects.filter(slug="imd").first()
        availability = source_availability(source) if source else {"state": "UNAVAILABLE", "last_success_at": None}
        queryset = OfficialAlert.objects.select_related("source")

        hazard = request.query_params.get("hazard")
        severity = request.query_params.get("severity")
        if hazard:
            queryset = queryset.filter(hazard=hazard)
        if severity:
            queryset = queryset.filter(severity=severity)
        current_only = request.query_params.get("current", "true").lower() != "false"
        if current_only:
            queryset = queryset.filter(status=AlertStatus.ACTIVE).filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
            )

        count = queryset.count()
        has_data = count > 0
        state = availability["state"] if has_data else "UNAVAILABLE"
        if has_data and state == "UNAVAILABLE":
            state = "STALE"
        return Response(
            {
                "state": state,
                "source": source_summary(source) if source else {},
                "last_success_at": availability.get("last_success_at"),
                "count": count,
                "results": OfficialAlertSerializer(queryset[:200], many=True).data,
                "note": (
                    "Only official IMD warnings are shown here. Absence of a warning is not proof "
                    "that conditions are safe."
                ),
                "reason": (
                    "IMD_API_KEY is not configured; official alert feed is unavailable."
                    if source and availability["state"] == "UNAVAILABLE"
                    else None
                ),
            }
        )


class AlertDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            alert = OfficialAlert.objects.select_related("source").get(pk=pk)
        except OfficialAlert.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Alert not found.", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"alert": OfficialAlertSerializer(alert).data})
