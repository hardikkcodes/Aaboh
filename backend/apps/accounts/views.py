from __future__ import annotations

from django.contrib.auth import logout as django_logout
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.core.schemas import DocumentedAPIView
from apps.incidents.models import ConfirmationKind, IncidentConfirmation, IncidentReport

from .models import SavedLocation, SavedRoute, UserPreference
from .routes import route_status
from .serializers import (
    AuthTokenSerializer,
    LoginSerializer,
    PreferenceUpdateSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    SavedLocationSerializer,
    SavedRouteSerializer,
    UserSerializer,
)

IMPACT_LEVELS = [(20, "local_guardian"), (5, "street_watcher"), (1, "reporter")]


class AuthThrottleMixin:
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RegisterView(AuthThrottleMixin, DocumentedAPIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(request=RegisterSerializer, responses={201: AuthTokenSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(AuthThrottleMixin, DocumentedAPIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: AuthTokenSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class LogoutView(DocumentedAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        if isinstance(request.auth, Token):
            request.auth.delete()
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(DocumentedAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(request=ProfileUpdateSerializer, responses={200: UserSerializer})
    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class SavedLocationListCreateView(DocumentedAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: SavedLocationSerializer(many=True)})
    def get(self, request):
        items = SavedLocation.objects.filter(user=request.user).select_related("area")
        return Response(SavedLocationSerializer(items, many=True).data)

    @extend_schema(request=SavedLocationSerializer, responses={201: SavedLocationSerializer})
    def post(self, request):
        serializer = SavedLocationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        location = serializer.save()
        return Response(SavedLocationSerializer(location).data, status=status.HTTP_201_CREATED)


class SavedLocationDetailView(DocumentedAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        deleted, _ = SavedLocation.objects.filter(pk=pk, user=request.user).delete()
        if not deleted:
            return Response(
                {"error": {"code": "not_found", "message": "Saved location not found.", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PreferenceView(DocumentedAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PreferenceUpdateSerializer, responses={200: UserSerializer})
    def patch(self, request):
        serializer = PreferenceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        preference, _ = UserPreference.objects.get_or_create(user=request.user)
        if "default_area" in data:
            from apps.locations.models import Area

            area_slug = data["default_area"]
            preference.default_area = Area.objects.filter(slug=area_slug).first() if area_slug else None
        for field in ("temperature_unit", "alerts_enabled", "quiet_hours", "telegram_chat_id"):
            if field in data:
                setattr(preference, field, data[field])
        preference.save()
        return Response(UserSerializer(request.user).data)


class SavedRouteListCreateView(DocumentedAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: SavedRouteSerializer(many=True)})
    def get(self, request):
        routes = SavedRoute.objects.filter(user=request.user)
        return Response(SavedRouteSerializer(routes, many=True).data)

    @extend_schema(request=SavedRouteSerializer, responses={201: SavedRouteSerializer})
    def post(self, request):
        serializer = SavedRouteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        route = serializer.save()
        return Response(SavedRouteSerializer(route).data, status=status.HTTP_201_CREATED)


class SavedRouteDetailView(DocumentedAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        get_object_or_404(SavedRoute, pk=pk, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SavedRouteStatusView(DocumentedAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        return Response(route_status(get_object_or_404(SavedRoute, pk=pk, user=request.user)))


class ImpactView(DocumentedAPIView):
    """A resident's own contribution summary. Never shown on public pages."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        reports = IncidentReport.objects.filter(reporter=request.user)
        confirmed = reports.filter(
            confirmations__kind=ConfirmationKind.STILL_THERE
        ).exclude(confirmations__user=request.user)
        score = reports.count() + IncidentConfirmation.objects.filter(user=request.user).count()
        level = next((name for minimum, name in IMPACT_LEVELS if score >= minimum), "new_neighbour")
        return Response(
            {
                "reports": reports.count(),
                "reports_confirmed_by_others": confirmed.distinct().count(),
                "confirmations_given": IncidentConfirmation.objects.filter(user=request.user).count(),
                "score": score,
                "level": level,
            }
        )
