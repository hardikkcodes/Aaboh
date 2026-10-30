from __future__ import annotations

import uuid

from django.db import models

from apps.core.fields import GeometryField
from apps.core.quality import DataState


class HazardType(models.TextChoices):
    HEAVY_RAIN = "heavy_rain", "Heavy rain"
    THUNDERSTORM = "thunderstorm", "Thunderstorm / lightning"
    HEATWAVE = "heatwave", "Heatwave"
    COLD_WAVE = "cold_wave", "Cold wave"
    CYCLONE = "cyclone", "Cyclone"
    FOG = "fog", "Fog"
    FLOOD = "flood", "Flood"
    OTHER = "other", "Other"


class AlertSeverity(models.TextChoices):
    MINOR = "minor", "Minor"
    MODERATE = "moderate", "Moderate"
    SEVERE = "severe", "Severe"
    EXTREME = "extreme", "Extreme"
    UNKNOWN = "unknown", "Unknown"


class AlertStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    EXPIRED = "expired", "Expired"
    CANCELLED = "cancelled", "Cancelled"


class OfficialAlert(models.Model):
    """An official warning exactly as issued, with its original severity and scope."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey("core.DataSource", on_delete=models.PROTECT, related_name="alerts")
    external_id = models.CharField(max_length=200)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    hazard = models.CharField(max_length=24, choices=HazardType.choices, default=HazardType.OTHER)
    severity = models.CharField(max_length=16, choices=AlertSeverity.choices, default=AlertSeverity.UNKNOWN)
    certainty = models.CharField(max_length=32, blank=True)
    urgency = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=16, choices=AlertStatus.choices, default=AlertStatus.ACTIVE)
    issued_at = models.DateTimeField()
    effective_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    areas_text = models.TextField(blank=True)
    geometry = GeometryField(
        allowed_types=("Polygon", "MultiPolygon"), null=True, blank=True
    )
    source_url = models.URLField(blank=True)
    raw = models.JSONField(default=dict, blank=True)
    retrieved_at = models.DateTimeField()
    quality_status = models.CharField(max_length=20, choices=DataState.CHOICES, default=DataState.AVAILABLE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-issued_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"], name="uniq_alert_external_id_per_source"
            )
        ]
        indexes = [
            models.Index(fields=["status", "expires_at"], name="alert_status_expiry_idx"),
            models.Index(fields=["hazard", "severity"], name="alert_hazard_severity_idx"),
            models.Index(fields=["issued_at"], name="alert_issued_idx"),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def is_current(self) -> bool:
        from django.utils import timezone

        if self.status != AlertStatus.ACTIVE:
            return False
        return self.expires_at is None or self.expires_at > timezone.now()
