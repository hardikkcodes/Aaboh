from __future__ import annotations

from django.contrib.auth import logout as django_logout
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import SavedLocation, UserPreference
from .serializers import (
    LoginSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    SavedLocationSerializer,
    UserSerializer,
)


class AuthThrottleMixin:
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RegisterView(AuthThrottleMixin, APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(AuthThrottleMixin, APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if isinstance(request.auth, Token):
            request.auth.delete()
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class SavedLocationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = SavedLocation.objects.filter(user=request.user).select_related("area")
        return Response(SavedLocationSerializer(items, many=True).data)

    def post(self, request):
        serializer = SavedLocationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        location = serializer.save()
        return Response(SavedLocationSerializer(location).data, status=status.HTTP_201_CREATED)


class SavedLocationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        deleted, _ = SavedLocation.objects.filter(pk=pk, user=request.user).delete()
        if not deleted:
            return Response(
                {"error": {"code": "not_found", "message": "Saved location not found.", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        preference, _ = UserPreference.objects.get_or_create(user=request.user)
        area_slug = request.data.get("default_area")
        if area_slug is not None:
            from apps.locations.models import Area

            preference.default_area = Area.objects.filter(slug=area_slug).first() if area_slug else None
        unit = request.data.get("temperature_unit")
        if unit in {"C", "F"}:
            preference.temperature_unit = unit
        preference.save()
        return Response(UserSerializer(request.user).data)
