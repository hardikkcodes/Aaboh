from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

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
    ENVIRONMENTAL_HAZARD = "environmental_hazard", "Environmental hazard"
    OTHER = "other", "Other environmental incident"


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
    description = models.TextField(max_length=2000)
    occurred_at = models.DateTimeField()
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
        ]

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
