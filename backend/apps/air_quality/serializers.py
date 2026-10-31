from __future__ import annotations

from rest_framework import serializers

from apps.core.serializers import source_summary

from .models import AQIMeasurement, AQIStation


class AQIMeasurementSerializer(serializers.ModelSerializer):
    aqi_basis = serializers.SerializerMethodField()
    units = serializers.SerializerMethodField()

    class Meta:
        model = AQIMeasurement
        fields = [
            "id",
            "measured_at",
            "retrieved_at",
            "aqi",
            "aqi_category",
            "aqi_basis",
            "pm25",
            "pm10",
            "no2",
            "so2",
            "co",
            "o3",
            "nh3",
            "units",
            "quality_status",
            "quality_flags",
        ]

    def get_aqi_basis(self, obj) -> dict:
        return (obj.raw or {}).get("aqi_basis") or {}

    def get_units(self, obj) -> dict:
        return (obj.raw or {}).get("units") or {}


class AQIStationSerializer(serializers.ModelSerializer):
    latest_measurement = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    distance_km = serializers.FloatField(read_only=True, required=False)

    class Meta:
        model = AQIStation
        fields = [
            "id",
            "external_id",
            "name",
            "city",
            "state",
            "point",
            "latitude",
            "longitude",
            "is_active",
            "latest_measurement",
            "distance_km",
            "source",
        ]

    def get_latest_measurement(self, obj):
        measurements = getattr(obj, "latest_measurements", None)
        if measurements is not None:
            return AQIMeasurementSerializer(measurements[0]).data if measurements else None
        latest = obj.measurements.order_by("-measured_at").first()
        return AQIMeasurementSerializer(latest).data if latest else None

    def get_source(self, obj) -> dict:
        return source_summary(obj.source)
