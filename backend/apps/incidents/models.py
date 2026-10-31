from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.fields import GeometryField
from apps.core.geometry import parse_geometry


def incident_upload_path(instance, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return f"incidents/{instance.incident_id}/{uuid.uuid4().hex}{suffix}"


class IncidentCategory(models.TextChoices):
    WATERLOGGING = "waterlogging", "Waterlogging"
    FLOODING = "flooding", "Local flooding"
    BLOCKED_DRAINAGE = "blocked_drainage", "Blocked drainage"
    FALLEN_TREE = "fallen_tree", "Fallen tree"
    ROAD_DISRUPTION = "road_disruption", "Road disruption"
    POWER_CUT = "power_cut", "Power cut"
    STAGNANT_WATER = "stagnant_water", "Stagnant water"
    TRANSPORT_DISRUPTION = "transport_disruption", "Transport disruption"
    ENVIRONMENTAL_HAZARD = "environmental_hazard", "Environmental hazard"
    OTHER = "other", "Other environmental incident"


# How long a report stays on the live map without a "still there" confirmation.
REPORT_LIFETIME_HOURS = {
    IncidentCategory.WATERLOGGING: 6,
    IncidentCategory.FLOODING: 12,
    IncidentCategory.BLOCKED_DRAINAGE: 72,
    IncidentCategory.FALLEN_TREE: 24,
    IncidentCategory.ROAD_DISRUPTION: 12,
    IncidentCategory.POWER_CUT: 6,
    IncidentCategory.STAGNANT_WATER: 168,
    IncidentCategory.TRANSPORT_DISRUPTION: 6,
    IncidentCategory.ENVIRONMENTAL_HAZARD: 24,
    IncidentCategory.OTHER: 12,
}
RESIDENT_CONFIRMATIONS_REQUIRED = 2
RESIDENT_CLEARS_REQUIRED = 2


class WaterDepth(models.TextChoices):
    ANKLE = "ankle", "Ankle deep"
    KNEE = "knee", "Knee deep"
    WAIST = "waist", "Waist deep"
    ABOVE_WAIST = "above_waist", "Above waist"


class Passability(models.TextChoices):
    CAR = "car", "Cars can pass"
    TWO_WHEELER = "two_wheeler", "Two-wheelers can pass"
    WALK = "walk", "Walking only"
    NONE = "none", "Not passable"


class ConfirmationKind(models.TextChoices):
    STILL_THERE = "still_there", "Still there"
    CLEARED = "cleared", "Cleared"
    WRONG = "wrong", "Looks wrong"


class ReportTrust(models.TextChoices):
    UNCONFIRMED = "unconfirmed", "Unconfirmed"
    RESIDENT_CONFIRMED = "resident_confirmed", "Confirmed by residents"
    MODERATOR_VERIFIED = "moderator_verified", "Verified by moderator"


class IncidentStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    VERIFIED = "VERIFIED", "Verified"
    RESOLVED = "RESOLVED", "Resolved"
    REJECTED = "REJECTED", "Rejected"
    EXPIRED = "EXPIRED", "Expired"
    DUPLICATE = "DUPLICATE", "Duplicate"


class IncidentReport(models.Model):
    """A community submission. Never represented as an official alert."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="incident_reports"
    )
    area = models.ForeignKey("locations.Area", on_delete=models.PROTECT, related_name="incident_reports")
    neighbourhood = models.ForeignKey(
        "locations.Neighbourhood",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="incident_reports",
    )
    category = models.CharField(max_length=32, choices=IncidentCategory.choices)
    description = models.TextField(max_length=2000, blank=True)
    occurred_at = models.DateTimeField()
    water_depth = models.CharField(max_length=16, choices=WaterDepth.choices, blank=True)
    passability = models.CharField(max_length=16, choices=Passability.choices, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    cleared_at = models.DateTimeField(null=True, blank=True)
    location_accuracy_m = models.FloatField(
        null=True, blank=True, help_text="Device-reported GPS accuracy. Never shown publicly."
    )
    point = GeometryField(geom_type="Point")
    latitude = models.FloatField()
    longitude = models.FloatField()
    address_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional coarse location description. Do not enter a home address.",
    )
    status = models.CharField(
        max_length=16, choices=IncidentStatus.choices, default=IncidentStatus.SUBMITTED
    )
    is_public = models.BooleanField(default=True)
    moderation_note = models.CharField(max_length=500, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_incidents",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    duplicate_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="duplicates"
    )
    source = models.ForeignKey(
        "core.DataSource", on_delete=models.PROTECT, related_name="incident_reports", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="incident_status_created_idx"),
            models.Index(fields=["category", "-created_at"], name="incident_category_idx"),
            models.Index(fields=["latitude", "longitude"], name="incident_coords_idx"),
            models.Index(fields=["area", "status"], name="incident_area_status_idx"),
            models.Index(fields=["reporter", "-created_at"], name="incident_reporter_idx"),
            models.Index(fields=["area", "expires_at"], name="incident_area_expiry_idx"),
        ]

    @property
    def is_active(self) -> bool:
        return bool(self.cleared_at is None and self.expires_at and self.expires_at > timezone.now())

    @property
    def confirmation_summary(self) -> dict[str, int]:
        """Vote counts. Only other residents count, so a reporter cannot confirm their own report."""
        summary = {kind: 0 for kind in ConfirmationKind.values}
        for confirmation in self.confirmations.all():
            if confirmation.user_id != self.reporter_id:
                summary[confirmation.kind] += 1
        return summary

    @property
    def trust(self) -> str:
        if self.status in {IncidentStatus.VERIFIED, IncidentStatus.RESOLVED}:
            return ReportTrust.MODERATOR_VERIFIED
        if self.confirmation_summary[ConfirmationKind.STILL_THERE] >= RESIDENT_CONFIRMATIONS_REQUIRED:
            return ReportTrust.RESIDENT_CONFIRMED
        return ReportTrust.UNCONFIRMED

    def clean(self):
        if not (-90 <= self.latitude <= 90 and -180 <= self.longitude <= 180):
            raise ValidationError("Latitude or longitude is out of range.")
        point = parse_geometry(self.point)
        if abs(point.y - self.latitude) > 1e-6 or abs(point.x - self.longitude) > 1e-6:
            raise ValidationError({"point": "Point coordinates and latitude/longitude disagree."})
        if (
            self.area_id
            and self.area.boundary
            and not parse_geometry(self.area.boundary).covers(point)
        ):
            raise ValidationError({"point": "Report location is outside the selected area."})

    def __str__(self) -> str:
        return f"{self.get_category_display()} at {self.latitude:.4f},{self.longitude:.4f}"


class IncidentConfirmation(models.Model):
    """One resident's current view of a report; changing it replaces the earlier vote."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(IncidentReport, on_delete=models.CASCADE, related_name="confirmations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    kind = models.CharField(max_length=16, choices=ConfirmationKind.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["incident", "user"], name="uniq_confirmation_per_user")
        ]


class SpotKind(models.TextChoices):
    COOL_SHADE = "cool_shade", "Cool or shaded place"
    DRINKING_WATER = "drinking_water", "Drinking water"
    SHELTER = "shelter", "Rain or storm shelter"


class CommunitySpot(models.Model):
    """A public place added by a resident. Nothing here is pre-loaded."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    area = models.ForeignKey("locations.Area", on_delete=models.CASCADE, related_name="community_spots")
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    kind = models.CharField(max_length=16, choices=SpotKind.choices)
    name = models.CharField(max_length=120)
    latitude = models.FloatField()
    longitude = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class IncidentAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(IncidentReport, on_delete=models.CASCADE, related_name="attachments")
    file = models.ImageField(upload_to=incident_upload_path)
    original_name = models.CharField(max_length=200)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class IncidentStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(IncidentReport, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=16, choices=IncidentStatus.choices, blank=True)
    to_status = models.CharField(max_length=16, choices=IncidentStatus.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["incident", "-created_at"], name="incident_history_idx")]
