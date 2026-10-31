from __future__ import annotations

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers

from apps.core.geometry import parse_geometry, point_geojson
from apps.locations.models import Area

from .models import SavedLocation, SavedRoute, UserPreference

User = get_user_model()
MIN_ROUTE_POINTS = 2
MAX_ROUTE_POINTS = 100
MAX_SAVED_ROUTES = 5


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
            "email_verified",
            "role",
            "is_moderator",
            "date_joined",
            "preferences",
        ]
        read_only_fields = [
            "id",
            "email",
            "email_verified",
            "role",
            "is_moderator",
            "date_joined",
            "preferences",
        ]

    def get_preferences(self, obj) -> dict:
        preference, _ = UserPreference.objects.get_or_create(user=obj)
        return {
            "temperature_unit": preference.temperature_unit,
            "default_area": preference.default_area.slug if preference.default_area else None,
            "alerts_enabled": preference.alerts_enabled,
            "quiet_hours": preference.quiet_hours,
            "telegram_chat_id": preference.telegram_chat_id,
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


def _checked_password(value: str, user=None) -> str:
    try:
        validate_password(value, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc
    return value


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value: str) -> str:
        return _checked_password(value)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_current_password(self, value: str) -> str:
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Your current password is not correct.")
        return value

    def validate_new_password(self, value: str) -> str:
        return _checked_password(value, self.context["request"].user)


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


class DeleteAccountSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_password(self, value: str) -> str:
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Your password is not correct.")
        return value


class AuthTokenSerializer(serializers.Serializer):
    token = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)


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


class PreferenceUpdateSerializer(serializers.Serializer):
    default_area = serializers.SlugField(required=False, allow_null=True, allow_blank=True)
    temperature_unit = serializers.ChoiceField(choices=["C", "F"], required=False)
    alerts_enabled = serializers.BooleanField(required=False)
    quiet_hours = serializers.BooleanField(required=False)
    telegram_chat_id = serializers.RegexField(r"^-?\d{1,20}$", required=False, allow_blank=True)


class SavedRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedRoute
        fields = ["id", "label", "points", "leave_at", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_label(self, value: str) -> str:
        value = value.strip()
        others = SavedRoute.objects.filter(user=self.context["request"].user, label=value)
        if self.instance:
            others = others.exclude(pk=self.instance.pk)
        if others.exists():
            raise serializers.ValidationError("You already have a route with this name.")
        return value

    def validate_points(self, value):
        if not isinstance(value, list) or not MIN_ROUTE_POINTS <= len(value) <= MAX_ROUTE_POINTS:
            raise serializers.ValidationError(
                f"Draw a route with {MIN_ROUTE_POINTS} to {MAX_ROUTE_POINTS} points."
            )
        cleaned = []
        for point in value:
            if not isinstance(point, list) or len(point) != 2:
                raise serializers.ValidationError("Each point must be [latitude, longitude].")
            try:
                latitude, longitude = float(point[0]), float(point[1])
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError("Coordinates must be numbers.") from exc
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise serializers.ValidationError("Coordinates are out of range.")
            cleaned.append([round(latitude, 5), round(longitude, 5)])
        return cleaned

    def create(self, validated_data):
        user = self.context["request"].user
        if SavedRoute.objects.filter(user=user).count() >= MAX_SAVED_ROUTES:
            raise serializers.ValidationError(f"Saved-route limit reached ({MAX_SAVED_ROUTES}).")
        return SavedRoute.objects.create(user=user, **validated_data)


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
        if (
            area
            and area.boundary
            and not parse_geometry(area.boundary).covers(parse_geometry(point_geojson(lat, lon)))
        ):
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
