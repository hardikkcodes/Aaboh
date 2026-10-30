from __future__ import annotations

import uuid

from django.db import models

from apps.core.quality import DataState


class PeriodType(models.TextChoices):
    ANNUAL = "annual", "Annual"
    SEASONAL = "seasonal", "Seasonal"
    MONTHLY = "monthly", "Monthly"


class ClimateBaseline(models.Model):
    """A named reference period used to calculate anomalies."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120, unique=True)
    dataset = models.CharField(max_length=80)
    variable = models.CharField(max_length=80)
    start_year = models.PositiveIntegerField()
    end_year = models.PositiveIntegerField()
    value = models.FloatField()
    unit = models.CharField(max_length=40)
    spatial_resolution_m = models.PositiveIntegerField(null=True, blank=True)
    source = models.ForeignKey("core.DataSource", on_delete=models.PROTECT, related_name="climate_baselines")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class ClimateMetric(models.Model):
    """Aggregated reanalysis metric for an area.

    ERA5-Land is ~9 km native resolution; these values are area aggregations and
    must never be presented as 1 km observations.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey("core.DataSource", on_delete=models.PROTECT, related_name="climate_metrics")
    area = models.ForeignKey("locations.Area", on_delete=models.CASCADE, related_name="climate_metrics")
    dataset = models.CharField(max_length=80)
    variable = models.CharField(max_length=80)
    period_type = models.CharField(max_length=16, choices=PeriodType.choices)
    season = models.CharField(max_length=20, blank=True)
    period_start = models.DateField()
    period_end = models.DateField()
    value = models.FloatField()
    unit = models.CharField(max_length=40)
    anomaly = models.FloatField(null=True, blank=True)
    baseline = models.ForeignKey(
        ClimateBaseline, on_delete=models.SET_NULL, null=True, blank=True, related_name="metrics"
    )
    spatial_resolution_m = models.PositiveIntegerField(null=True, blank=True)
    quality_status = models.CharField(max_length=20, choices=DataState.CHOICES, default=DataState.AVAILABLE)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-period_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "area", "dataset", "variable", "period_type", "season", "period_start"],
                name="uniq_climate_metric_period",
            )
        ]
        indexes = [
            models.Index(fields=["area", "variable", "-period_start"], name="climate_area_var_idx"),
            models.Index(fields=["period_type", "season"], name="climate_period_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.area.slug} {self.variable} {self.period_start}"
