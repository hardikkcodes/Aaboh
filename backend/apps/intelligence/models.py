from __future__ import annotations

import uuid

from django.db import models

from apps.core.quality import DataState


class InsightSeverity(models.TextChoices):
    INFO = "info", "Information"
    CAUTION = "caution", "Caution"
    WARNING = "warning", "Warning"


class Recommendation(models.Model):
    """A persisted, rule-based briefing item. Every item references evidence."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    area = models.ForeignKey("locations.Area", on_delete=models.CASCADE, related_name="recommendations")
    rule_id = models.CharField(max_length=80)
    kind = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    body = models.TextField()
    severity = models.CharField(max_length=16, choices=InsightSeverity.choices, default=InsightSeverity.INFO)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-generated_at"]
        indexes = [models.Index(fields=["area", "-generated_at"], name="recommendation_area_idx")]

    def __str__(self) -> str:
        return self.title


class RecommendationEvidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recommendation = models.ForeignKey(
        Recommendation, on_delete=models.CASCADE, related_name="evidence"
    )
    evidence_type = models.CharField(max_length=40)
    label = models.CharField(max_length=200)
    source = models.ForeignKey(
        "core.DataSource", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    observed_at = models.DateTimeField(null=True, blank=True)
    reference = models.JSONField(default=dict, blank=True)
    source_url = models.URLField(blank=True)
    quality_status = models.CharField(max_length=20, choices=DataState.CHOICES, default=DataState.AVAILABLE)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.label
