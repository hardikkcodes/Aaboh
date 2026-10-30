from __future__ import annotations

from rest_framework import serializers

from .models import ClimateBaseline, ClimateMetric


class ClimateBaselineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClimateBaseline
        fields = [
            "id",
            "name",
            "dataset",
            "variable",
            "start_year",
            "end_year",
            "value",
            "unit",
            "spatial_resolution_m",
        ]


class ClimateMetricSerializer(serializers.ModelSerializer):
    baseline = ClimateBaselineSerializer(read_only=True)

    class Meta:
        model = ClimateMetric
        fields = [
            "id",
            "dataset",
            "variable",
            "period_type",
            "season",
            "period_start",
            "period_end",
            "value",
            "unit",
            "anomaly",
            "spatial_resolution_m",
            "quality_status",
            "baseline",
            "metadata",
        ]
