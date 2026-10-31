from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, ValidationError
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.permissions import IsModerator
from apps.core.schemas import DocumentedAPIView
from apps.locations.models import Area

from .models import IncidentCategory, IncidentReport, IncidentStatus
from .serializers import (
    IncidentCreateSerializer,
    IncidentDetailSerializer,
    IncidentEditSerializer,
    IncidentListSerializer,
    IncidentModerationSerializer,
    IncidentStatusHistoryPublicSerializer,
    verification_state,
)
from .services import (
    moderate_incident,
    visible_incidents,
)

EDITABLE_STATUSES = {IncidentStatus.SUBMITTED, IncidentStatus.UNDER_REVIEW}
HIDDEN_PUBLIC_STATUSES = {IncidentStatus.REJECTED, IncidentStatus.DUPLICATE, IncidentStatus.EXPIRED}


def _is_moderator(request) -> bool:
    return bool(
        request.user
        and request.user.is_authenticated
        and getattr(request.user, "is_moderator", False)
    )


def _detail_queryset():
    return IncidentReport.objects.select_related(
        "area", "neighbourhood", "reporter", "source", "duplicate_of"
    ).prefetch_related("attachments", "status_history")


class IncidentListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "incident_create"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return IncidentCreateSerializer
        return IncidentListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get_queryset(self):
        request = self.request
        queryset = _detail_queryset()
        queryset = visible_incidents(queryset, request.user)
        mine = request.query_params.get("mine", "false").lower() == "true"
        if mine:
            if not request.user or not request.user.is_authenticated:
                raise NotAuthenticated("Authentication is required to list your reports.")
            queryset = queryset.filter(reporter=request.user)

        category = request.query_params.get("category")
        if category:
            if category not in IncidentCategory.values:
                raise ValidationError({"category": "Unknown incident category."})
            queryset = queryset.filter(category=category)
        status_filter = request.query_params.get("status")
        if status_filter:
            if status_filter not in IncidentStatus.values:
                raise ValidationError({"status": "Unknown incident status."})
            queryset = queryset.filter(status=status_filter)
        area_slug = request.query_params.get("area")
        if area_slug:
            queryset = queryset.filter(area__slug=area_slug)
        neighbourhood_slug = request.query_params.get("neighbourhood")
        if neighbourhood_slug:
            queryset = queryset.filter(neighbourhood__slug=neighbourhood_slug)

        since_hours = request.query_params.get("since_hours")
        if since_hours:
            try:
                hours = min(max(int(since_hours), 1), 24 * 90)
            except ValueError as exc:
                raise ValidationError({"since_hours": "Must be an integer."}) from exc
            queryset = queryset.filter(created_at__gte=timezone.now() - timedelta(hours=hours))

        bbox = request.query_params.get("bbox")
        if bbox:
            try:
                min_lon, min_lat, max_lon, max_lat = [float(part) for part in bbox.split(",")]
            except ValueError as exc:
                raise ValidationError({"bbox": "Use min_lon,min_lat,max_lon,max_lat."}) from exc
            queryset = queryset.filter(
                latitude__gte=min_lat,
                latitude__lte=max_lat,
                longitude__gte=min_lon,
                longitude__lte=max_lon,
            )

        if not (mine or _is_moderator(request)):
            queryset = queryset.exclude(status__in=HIDDEN_PUBLIC_STATUSES)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        incident = serializer.save()
        detail = IncidentDetailSerializer(
            incident,
            context={"request": request},
        ).data
        return Response(detail, status=status.HTTP_201_CREATED)


class IncidentDetailView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.request.method in {"PATCH", "PUT"}:
            return IncidentEditSerializer
        return IncidentDetailSerializer

    def get_object(self):
        queryset = visible_incidents(_detail_queryset(), self.request.user)
        try:
            incident = queryset.get(pk=self.kwargs["pk"])
        except IncidentReport.DoesNotExist as exc:
            from rest_framework.exceptions import NotFound

            raise NotFound("Community report not found.") from exc
        return incident

    def update(self, request, *args, **kwargs):
        incident = self.get_object()
        user = request.user
        is_moderator = _is_moderator(request)
        if not user or not user.is_authenticated:
            raise NotAuthenticated("Authentication is required to edit a report.")
        if not (is_moderator or incident.reporter_id == user.id):
            raise PermissionDenied("Only the reporter or a moderator may edit this report.")
        if not is_moderator and incident.status not in EDITABLE_STATUSES:
            raise ValidationError(
                {"status": "Reports can only be edited while they are unverified or under review."}
            )
        serializer = self.get_serializer(incident, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(IncidentDetailSerializer(incident, context={"request": request}).data)


class IncidentModerateView(DocumentedAPIView):
    permission_classes = [IsModerator]

    @extend_schema(request=IncidentModerationSerializer, responses={200: IncidentDetailSerializer})
    def post(self, request, pk):
        try:
            incident = _detail_queryset().get(pk=pk)
        except IncidentReport.DoesNotExist as exc:
            from rest_framework.exceptions import NotFound

            raise NotFound("Community report not found.") from exc
        serializer = IncidentModerationSerializer(
            data=request.data, context={"incident": incident, "request": request}
        )
        serializer.is_valid(raise_exception=True)
        incident = moderate_incident(
            incident,
            moderator=request.user,
            to_status=serializer.validated_data["status"],
            note=serializer.validated_data.get("note", ""),
            duplicate=serializer.validated_data.get("duplicate"),
            is_public=serializer.validated_data.get("is_public"),
        )
        return Response(IncidentDetailSerializer(incident, context={"request": request}).data)


class IncidentHistoryView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        queryset = visible_incidents(_detail_queryset(), request.user)
        try:
            incident = queryset.get(pk=pk)
        except IncidentReport.DoesNotExist as exc:
            from rest_framework.exceptions import NotFound

            raise NotFound("Community report not found.") from exc
        history = incident.status_history.all().order_by("created_at")
        return Response(
            {
                "incident": str(incident.id),
                "verification_state": verification_state(incident.status),
                "count": history.count(),
                "results": IncidentStatusHistoryPublicSerializer(history, many=True).data,
                "note": "Moderator identities are never exposed publicly.",
            }
        )


class IncidentSummaryView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        area_slug = request.query_params.get("area", "kolkata")
        area = Area.objects.filter(slug=area_slug, is_active=True).first()
        if area is None:
            raise ValidationError({"area": f"Unknown area: {area_slug}"})
        since = timezone.now() - timedelta(hours=24 * 7)
        base = IncidentReport.objects.filter(area=area, is_public=True, created_at__gte=since).exclude(
            status__in=[IncidentStatus.REJECTED, IncidentStatus.DUPLICATE]
        )
        by_status = {
            row["status"]: row["count"]
            for row in base.values("status").annotate(count=Count("id")).order_by()
        }
        by_category = {
            row["category"]: row["count"]
            for row in base.values("category").annotate(count=Count("id")).order_by()
        }
        recent = base.filter(
            status__in=[IncidentStatus.SUBMITTED, IncidentStatus.UNDER_REVIEW]
        ).count()
        return Response(
            {
                "area": {"slug": area.slug, "name": area.name},
                "window_hours": 24 * 7,
                "total": base.count(),
                "unverified": recent,
                "verified": base.filter(
                    status__in=[IncidentStatus.VERIFIED, IncidentStatus.RESOLVED]
                ).count(),
                "by_status": by_status,
                "by_category": by_category,
                "note": (
                    "Community reports are observations submitted by residents. They are not official "
                    "alerts and may be inaccurate until moderated."
                ),
            }
        )
