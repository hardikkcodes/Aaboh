from __future__ import annotations

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.quality import DataState, source_availability
from apps.core.schemas import DocumentedAPIView
from apps.core.serializers import source_summary
from apps.locations.models import Area

from .models import AlertStatus, OfficialAlert
from .serializers import OfficialAlertSerializer
from .services import AlertMatch, alert_match, official_alert_source

ALERT_NOTE = (
    "Only source-issued official alerts are shown, matched using the area text published by "
    "the issuing agency. Some alerts only name the state, so check the bulletin for your "
    "district. Absence of an alert is not proof that conditions are safe."
)


class AlertListView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        area_slug = request.query_params.get("area", "kolkata")
        area = Area.objects.filter(slug=area_slug, is_active=True).first()
        if area is None:
            raise ValidationError({"area": f"Unknown area: {area_slug}"})
        source = official_alert_source()
        availability = (
            source_availability(source)
            if source
            else {"state": DataState.UNAVAILABLE, "last_success_at": None}
        )
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

        alerts = list(queryset) if current_only else list(queryset[:2000])
        scoped = []
        for alert in alerts:
            alert.match = alert_match(alert, area)
            if alert.match:
                scoped.append(alert)
        scoped.sort(key=lambda alert: alert.match != AlertMatch.NAMED)
        if not current_only:
            scoped = scoped[:200]
        named = sum(1 for alert in scoped if alert.match == AlertMatch.NAMED)

        feed_healthy = availability["state"] in {DataState.AVAILABLE, DataState.PARTIAL}
        if feed_healthy:
            state = availability["state"]
            reason = None
            if named:
                feed_message = f"{named} active official warning(s) name {area.name}."
            elif scoped:
                feed_message = (
                    f"{len(scoped)} state-level warning(s) may include {area.name}. "
                    "Check the bulletin for your district."
                )
            else:
                feed_message = f"The official alert feed is reachable. No active warning covers {area.name} right now."
        elif scoped:
            state = DataState.STALE
            reason = (
                "The latest alert-feed refresh failed, so these alerts may be stale. Check the "
                "issuing agency before acting."
            )
            feed_message = reason
        else:
            state = availability["state"]
            reason = f"The official alert feed is unavailable and no stored alert covers {area.name}."
            feed_message = reason

        return Response(
            {
                "state": state,
                "provider": source.slug if source else None,
                "source": source_summary(source) if source else {},
                "last_success_at": availability.get("last_success_at"),
                "last_attempt_at": availability.get("last_attempt_at"),
                "count": len(scoped),
                "named_count": named,
                "results": OfficialAlertSerializer(scoped, many=True).data,
                "scope_terms": list(settings.SACHET_SCOPE_TERMS) if source and source.slug == "sachet" else [],
                "feed_message": feed_message,
                "note": ALERT_NOTE,
                "reason": reason,
            }
        )


class AlertDetailView(DocumentedAPIView):
    permission_classes = [AllowAny]

    @extend_schema(operation_id="alerts_detail")
    def get(self, request, pk):
        try:
            alert = OfficialAlert.objects.select_related("source").get(pk=pk)
        except OfficialAlert.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Alert not found.", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"alert": OfficialAlertSerializer(alert).data})
