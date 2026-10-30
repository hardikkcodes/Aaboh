from __future__ import annotations

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers

from apps.core.geometry import parse_geometry, point_geojson
from apps.locations.models import Area

from .models import SavedLocation, UserPreference

User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    is_moderator = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "display_name", "role", "is_moderator"]
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    is_moderator = serializers.BooleanField(read_only=True)
    preferences = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "display_name",
            "role",
            "is_moderator",
            "date_joined",
            "preferences",
        ]
        read_only_fields = ["id", "email", "role", "is_moderator", "date_joined", "preferences"]

    def get_preferences(self, obj) -> dict:
        preference, _ = UserPreference.objects.get_or_create(user=obj)
        return {
            "temperature_unit": preference.temperature_unit,
            "default_area": preference.default_area.slug if preference.default_area else None,
        }


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    display_name = serializers.CharField(max_length=80, required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalized

    def validate_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc
        return value

    @transaction.atomic
    def create(self, validated_data):
        email = validated_data["email"]
        base_username = slugify(email.split("@")[0])[:120] or "user"
        username = base_username
        suffix = 1
        while User.objects.filter(username=username).exists():
            suffix += 1
            username = f"{base_username}-{suffix}"
        user = User(
            username=username,
            email=email,
            display_name=validated_data.get("display_name", "").strip(),
        )
        user.set_password(validated_data["password"])
        user.save()
        UserPreference.objects.get_or_create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        authenticated = None
        if user is not None:
            authenticated = authenticate(
                request=self.context.get("request"),
                username=user.username,
                password=attrs["password"],
            )
        if authenticated is None:
            # Do not reveal whether the email exists.
            raise serializers.ValidationError("Invalid email or password.")
        if not authenticated.is_active:
            raise serializers.ValidationError("This account is inactive.")
        attrs["user"] = authenticated
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["display_name"]

    def validate_display_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Display name cannot be empty.")
        return value


class SavedLocationSerializer(serializers.ModelSerializer):
    area = serializers.SlugRelatedField(slug_field="slug", queryset=Area.objects.all(), required=False, allow_null=True)
    point = serializers.JSONField(read_only=True)

    class Meta:
        model = SavedLocation
        fields = ["id", "label", "area", "latitude", "longitude", "point", "created_at"]
        read_only_fields = ["id", "point", "created_at"]

    def validate(self, attrs):
        lat = attrs.get("latitude", getattr(self.instance, "latitude", None))
        lon = attrs.get("longitude", getattr(self.instance, "longitude", None))
        if lat is None or lon is None:
            raise serializers.ValidationError({"latitude": "Latitude and longitude are required."})
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise serializers.ValidationError({"latitude": "Coordinates are out of range."})
        area = attrs.get("area")
        if area and area.boundary:
            if not parse_geometry(area.boundary).covers(parse_geometry(point_geojson(lat, lon))):
                raise serializers.ValidationError({"area": "Selected point is outside this area."})
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        if SavedLocation.objects.filter(user=user).count() >= 20:
            raise serializers.ValidationError("Saved-location limit reached (20).")
        lat, lon = validated_data["latitude"], validated_data["longitude"]
        return SavedLocation.objects.create(
            user=user,
            point=point_geojson(lat, lon),
            **validated_data,
        )
