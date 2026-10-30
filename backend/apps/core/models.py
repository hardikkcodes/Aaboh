"""Provenance models shared by every environmental domain."""

from __future__ import annotations

import uuid

from django.db import models


class ProviderType(models.TextChoices):
    OFFICIAL = "official", "Official authority"
    FORECAST_MODEL = "forecast_model", "Forecast model"
    REANALYSIS = "reanalysis", "Reanalysis dataset"
    EARTH_OBSERVATION = "earth_observation", "Earth observation"
    COMMUNITY = "community", "Community contributed"
    SUPPLEMENTARY = "supplementary", "Supplementary source"
    DEVELOPMENT_FIXTURE = "development_fixture", "Development fixture"


class DataSource(models.Model):
    """A stable description of where a dataset comes from and how it may be used."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    provider_type = models.CharField(max_length=32, choices=ProviderType.choices)
    description = models.TextField(blank=True)
    homepage_url = models.URLField(blank=True)
    license_name = models.CharField(max_length=160, blank=True)
    license_url = models.URLField(blank=True)
    attribution = models.CharField(max_length=300, blank=True)
    spatial_resolution_m = models.PositiveIntegerField(null=True, blank=True)
    temporal_resolution = models.CharField(max_length=80, blank=True)
    expected_refresh_minutes = models.PositiveIntegerField(
        null=True, blank=True, help_text="Used to flag stale data; null means no expectation."
    )
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def is_official(self) -> bool:
        return self.provider_type == ProviderType.OFFICIAL


class IngestionRunStatus(models.TextChoices):
    RUNNING = "RUNNING", "Running"
    SUCCESS = "SUCCESS", "Success"
    PARTIAL = "PARTIAL", "Partial"
    FAILED = "FAILED", "Failed"


class IngestionRun(models.Model):
    """Audit record for every external data acquisition attempt."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name="ingestion_runs")
    status = models.CharField(
        max_length=16, choices=IngestionRunStatus.choices, default=IngestionRunStatus.RUNNING
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    records_fetched = models.PositiveIntegerField(default=0)
    records_written = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    params = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["source", "-started_at"], name="ingest_source_started_idx"),
            models.Index(fields=["status"], name="ingest_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.source.slug} {self.status} {self.started_at:%Y-%m-%d %H:%M}"
