from __future__ import annotations

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.fields import GeometryField
from apps.core.quality import DataState


class WeatherKind(models.TextChoices):
    CURRENT = "CURRENT", "Current conditions"
    HOURLY = "HOURLY", "Hourly forecast"
    DAILY = "DAILY", "Daily forecast"


class WeatherLocation(models.Model):
    """A provider-specific forecast point associated with an area."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    area = models.ForeignKey("locations.Area", on_delete=models.CASCADE, related_name="weather_locations")
    name = models.CharField(max_length=160)
    point = GeometryField(geom_type="Point")
    latitude = models.FloatField()
    longitude = models.FloatField()
    elevation_m = models.FloatField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    source = models.ForeignKey("core.DataSource", on_delete=models.PROTECT, related_name="weather_locations")
    provider_location_key = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "provider_location_key"], name="uniq_weather_location_provider_key"
            )
        ]
        indexes = [models.Index(fields=["area", "source"], name="weather_loc_area_source_idx")]

    def __str__(self) -> str:
        return f"{self.name} ({self.source.slug})"


class WeatherRecord(models.Model):
    """Normalised weather values for one location, kind and valid time."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.ForeignKey(WeatherLocation, on_delete=models.CASCADE, related_name="records")
    source = models.ForeignKey("core.DataSource", on_delete=models.PROTECT, related_name="weather_records")
    kind = models.CharField(max_length=8, choices=WeatherKind.choices)
    valid_time = models.DateTimeField(help_text="Observation time or forecast valid time (UTC).")
    issued_at = models.DateTimeField(null=True, blank=True)
    retrieved_at = models.DateTimeField()
    temperature_c = models.FloatField(null=True, blank=True)
    temperature_max_c = models.FloatField(null=True, blank=True)
    temperature_min_c = models.FloatField(null=True, blank=True)
    apparent_temperature_c = models.FloatField(null=True, blank=True)
    apparent_temperature_max_c = models.FloatField(null=True, blank=True)
    apparent_temperature_min_c = models.FloatField(null=True, blank=True)
    dew_point_c = models.FloatField(null=True, blank=True)
    relative_humidity = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    precipitation_mm = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    precipitation_probability = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    rain_mm = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    showers_mm = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    wind_speed_kmh = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    wind_gust_kmh = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    wind_direction_deg = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(360)]
    )
    cloud_cover = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    shortwave_radiation_wm2 = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    pressure_hpa = models.FloatField(null=True, blank=True)
    visibility_m = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0)])
    weather_code = models.IntegerField(null=True, blank=True)
    is_day = models.BooleanField(null=True, blank=True)
    quality_status = models.CharField(max_length=20, choices=DataState.CHOICES, default=DataState.AVAILABLE)
    raw = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["valid_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["location", "source", "kind", "valid_time"], name="uniq_weather_record_slot"
            )
        ]
        indexes = [
            models.Index(fields=["location", "kind", "valid_time"], name="weather_rec_slot_idx"),
            models.Index(fields=["valid_time"], name="weather_rec_valid_idx"),
            models.Index(fields=["kind", "retrieved_at"], name="weather_rec_retrieved_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.location} {self.kind} {self.valid_time:%Y-%m-%d %H:%M}"

    @property
    def is_forecast(self) -> bool:
        return self.kind in {WeatherKind.HOURLY, WeatherKind.DAILY}
