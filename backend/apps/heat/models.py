from __future__ import annotations

import uuid

from django.db import models


class ModelTask(models.TextChoices):
    LST = "lst_estimation", "Daytime land-surface temperature estimation"
    WATERLOGGING = "waterlogging_susceptibility", "Waterlogging susceptibility"
    AQI = "aqi_forecast", "Station AQI forecast"


class ModelVersion(models.Model):
    """Registry entry for a reproducible, evaluated model artifact."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    version = models.CharField(max_length=40)
    task = models.CharField(max_length=48, choices=ModelTask.choices, default=ModelTask.LST)
    algorithm = models.CharField(max_length=80)
    target = models.CharField(max_length=80)
    dataset_version = models.CharField(max_length=80)
    feature_schema = models.JSONField(default=dict, blank=True)
    training_period_start = models.DateField(null=True, blank=True)
    training_period_end = models.DateField(null=True, blank=True)
    metrics = models.JSONField(default=dict, blank=True)
    artifact_path = models.CharField(max_length=500, blank=True)
    code_commit = models.CharField(max_length=64, blank=True)
    training_config = models.JSONField(default=dict, blank=True)
    trained_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    is_operational = models.BooleanField(
        default=False,
        help_text="True only when evaluation and data-quality gates have been satisfied.",
    )
    limitations = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["name", "version"], name="uniq_model_name_version")
        ]

    def __str__(self) -> str:
        return f"{self.name} {self.version}"


class PredictionRunStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    RUNNING = "RUNNING", "Running"
    COMPLETE = "COMPLETE", "Complete"
    FAILED = "FAILED", "Failed"


class PredictionRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_version = models.ForeignKey(ModelVersion, on_delete=models.PROTECT, related_name="prediction_runs")
    area = models.ForeignKey("locations.Area", on_delete=models.CASCADE, related_name="prediction_runs")
    status = models.CharField(
        max_length=16, choices=PredictionRunStatus.choices, default=PredictionRunStatus.QUEUED
    )
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-generated_at"]
        indexes = [models.Index(fields=["area", "-generated_at"], name="pred_run_area_idx")]

    def __str__(self) -> str:
        return f"{self.model_version} {self.area.slug} {self.status}"


class CellPrediction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(PredictionRun, on_delete=models.CASCADE, related_name="predictions")
    cell = models.ForeignKey("locations.GridCell", on_delete=models.CASCADE, related_name="heat_predictions")
    predicted_lst_c = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "cell"], name="uniq_cell_prediction_run_cell")
        ]
        indexes = [models.Index(fields=["cell"], name="cell_prediction_cell_idx")]
