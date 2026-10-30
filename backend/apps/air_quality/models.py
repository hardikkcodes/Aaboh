from __future__ import annotations

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.fields import GeometryField
from apps.core.quality import DataState


class AQIStation(models.Model):
    """A real monitoring station with its published coordinates and identity."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey("core.DataSource", on_delete=models.PROTECT, related_name="aqi_stations")
    external_id = models.CharField(max_length=160)
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=120, blank=True)
    point = GeometryField(geom_type="Point")
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"], name="uniq_aqi_station_external_id_per_source"
            )
        ]
        indexes = [
            models.Index(fields=["latitude", "longitude"], name="aqi_station_coords_idx"),
            models.Index(fields=["city", "is_active"], name="aqi_station_city_active_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class AQIMeasurement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    station = models.ForeignKey(AQIStation, on_delete=models.CASCADE, related_name="measurements")
    source = models.ForeignKey("core.DataSource", on_delete=models.PROTECT, related_name="aqi_measurements")
    measured_at = models.DateTimeField()
    retrieved_at = models.DateTimeField()
    aqi = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1000)])
    aqi_category = models.CharField(max_length=60, blank=True)
    pm25 = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    pm10 = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    no2 = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    so2 = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    co = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    o3 = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    quality_status = models.CharField(max_length=20, choices=DataState.CHOICES, default=DataState.AVAILABLE)
    quality_flags = models.JSONField(default=list, blank=True)
    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-measured_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["station", "measured_at"], name="uniq_aqi_measurement_station_time"
            )
        ]
        indexes = [
            models.Index(fields=["station", "-measured_at"], name="aqi_measure_station_time_idx"),
            models.Index(fields=["measured_at"], name="aqi_measure_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.station} {self.measured_at:%Y-%m-%d %H:%M}"
