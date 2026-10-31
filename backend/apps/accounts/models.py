from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.fields import GeometryField
from apps.core.geometry import parse_geometry, point_geojson


class UserRole(models.TextChoices):
    PUBLIC = "public", "Public user"
    MODERATOR = "moderator", "Moderator"
    ADMIN = "admin", "Administrator"


class User(AbstractUser):
    """Custom user model introduced before the first migration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=80, blank=True)
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.PUBLIC)
    email_verified = models.BooleanField(default=False)

    REQUIRED_FIELDS = ["email"]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        if not self.display_name:
            self.display_name = self.username
        super().save(*args, **kwargs)

    @property
    def is_moderator(self) -> bool:
        return self.role in {UserRole.MODERATOR, UserRole.ADMIN} or self.is_staff

    def __str__(self) -> str:
        return self.display_name or self.email or self.username


class UserPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="preferences")
    default_area = models.ForeignKey(
        "locations.Area", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    temperature_unit = models.CharField(
        max_length=1, choices=[("C", "Celsius"), ("F", "Fahrenheit")], default="C"
    )
    alerts_enabled = models.BooleanField(default=True)
    quiet_hours = models.BooleanField(
        default=True, help_text="Hold non-official Telegram alerts from 22:00 to 06:00 IST."
    )
    telegram_chat_id = models.CharField(max_length=32, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Preferences for {self.user}"


class SavedRoute(models.Model):
    """A private corridor drawn by a user as a short list of [latitude, longitude] points."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_routes")
    label = models.CharField(max_length=80)
    points = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "label"], name="uniq_saved_route_label_per_user")
        ]

    def __str__(self) -> str:
        return self.label


class SavedLocation(models.Model):
    """A private, user-chosen map point. Never exposed through public endpoints."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_locations")
    label = models.CharField(max_length=80)
    area = models.ForeignKey(
        "locations.Area", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    point = GeometryField(geom_type="Point")
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "label"], name="uniq_saved_location_label_per_user")
        ]
        indexes = [models.Index(fields=["user", "-created_at"], name="saved_loc_user_idx")]

    def clean(self):
        if not (-90 <= self.latitude <= 90 and -180 <= self.longitude <= 180):
            raise ValidationError("Latitude or longitude is out of range.")
        expected = parse_geometry(self.point)
        if expected.geom_type != "Point":
            raise ValidationError({"point": "Saved locations require a Point geometry."})
        if abs(expected.y - self.latitude) > 1e-6 or abs(expected.x - self.longitude) > 1e-6:
            raise ValidationError({"point": "Point coordinates and latitude/longitude disagree."})

    def save(self, *args, **kwargs):
        if not self.point and self.latitude is not None and self.longitude is not None:
            self.point = point_geojson(self.latitude, self.longitude)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.label
