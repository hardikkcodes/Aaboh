from __future__ import annotations

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.fields import GeometryField


class SatelliteScene(models.Model):
    """A satellite scene and its processing provenance."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey("core.DataSource", on_delete=models.PROTECT, related_name="satellite_scenes")
    scene_id = models.CharField(max_length=200)
    platform = models.CharField(max_length=80, blank=True)
    collection = models.CharField(max_length=80, blank=True)
    acquired_at = models.DateTimeField()
    cloud_cover_pct = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    processing_level = models.CharField(max_length=80, blank=True)
    bounds = GeometryField(allowed_types=("Polygon", "MultiPolygon"), null=True, blank=True)
    source_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-acquired_at"]
        constraints = [
            models.UniqueConstraint(fields=["source", "scene_id"], name="uniq_scene_id_per_source")
        ]
        indexes = [models.Index(fields=["acquired_at"], name="scene_acquired_idx")]

    def __str__(self) -> str:
        return self.scene_id


class EnvironmentalObservation(models.Model):
    """Per-grid-cell aggregation of satellite-derived indices for one scene.

    LST is a land-surface temperature retrieved from thermal bands, not air
    temperature, and its native thermal resolution is coarser than 1 km.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scene = models.ForeignKey(SatelliteScene, on_delete=models.CASCADE, related_name="observations")
    cell = models.ForeignKey("locations.GridCell", on_delete=models.CASCADE, related_name="observations")
    observed_on = models.DateField()
    lst_c = models.FloatField(null=True, blank=True)
    ndvi = models.FloatField(null=True, blank=True)
    ndbi = models.FloatField(null=True, blank=True)
    mndwi = models.FloatField(null=True, blank=True)
    valid_pixel_count = models.PositiveIntegerField(default=0)
    valid_pixel_fraction = models.FloatField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    quality_flags = models.JSONField(default=list, blank=True)
    processing_version = models.CharField(max_length=60)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-observed_on"]
        constraints = [
            models.UniqueConstraint(fields=["scene", "cell"], name="uniq_observation_scene_cell")
        ]
        indexes = [
            models.Index(fields=["cell", "-observed_on"], name="env_obs_cell_date_idx"),
            models.Index(fields=["observed_on"], name="env_obs_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.cell.code} {self.observed_on}"
