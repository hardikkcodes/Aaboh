from __future__ import annotations

from django.contrib.auth import logout as django_logout
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.core.schemas import DocumentedAPIView

from .models import SavedLocation, UserPreference
from .serializers import (
    AuthTokenSerializer,
    LoginSerializer,
    PreferenceUpdateSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    SavedLocationSerializer,
    UserSerializer,
)


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
        if "temperature_unit" in data:
            preference.temperature_unit = data["temperature_unit"]
        preference.save()
        return Response(UserSerializer(request.user).data)
