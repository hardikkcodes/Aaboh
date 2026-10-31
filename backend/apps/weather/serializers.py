from __future__ import annotations

from rest_framework import serializers

from .conditions import condition_for_code
from .models import WeatherLocation, WeatherRecord


class WeatherRecordSerializer(serializers.ModelSerializer):
    condition = serializers.SerializerMethodField()

    class Meta:
        model = WeatherRecord
        fields = [
            "id",
            "kind",
            "valid_time",
            "issued_at",
            "retrieved_at",
            "temperature_c",
            "temperature_max_c",
            "temperature_min_c",
            "apparent_temperature_c",
            "apparent_temperature_max_c",
            "apparent_temperature_min_c",
            "dew_point_c",
            "relative_humidity",
            "precipitation_mm",
            "precipitation_probability",
            "rain_mm",
            "showers_mm",
            "wind_speed_kmh",
            "wind_gust_kmh",
            "wind_direction_deg",
            "cloud_cover",
            "shortwave_radiation_wm2",
            "pressure_hpa",
            "visibility_m",
            "uv_index",
            "weather_code",
            "is_day",
            "quality_status",
            "condition",
        ]

    def get_condition(self, obj) -> dict:
        return condition_for_code(obj.weather_code)


class WeatherLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherLocation
        fields = ["id", "name", "latitude", "longitude", "elevation_m", "timezone"]
