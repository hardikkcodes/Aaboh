from __future__ import annotations

from rest_framework import serializers

from .models import CellPrediction, ModelVersion, PredictionRun


class ModelVersionSerializer(serializers.ModelSerializer):
    task_label = serializers.CharField(source="get_task_display", read_only=True)

    class Meta:
        model = ModelVersion
        fields = [
            "id",
            "name",
            "version",
            "task",
            "task_label",
            "algorithm",
            "target",
            "dataset_version",
            "feature_schema",
            "training_period_start",
            "training_period_end",
            "metrics",
            "artifact_path",
            "code_commit",
            "training_config",
            "trained_at",
            "is_active",
            "is_operational",
            "limitations",
            "created_at",
        ]


class PredictionRunSerializer(serializers.ModelSerializer):
    model = ModelVersionSerializer(source="model_version", read_only=True)

    class Meta:
        model = PredictionRun
        fields = ["id", "status", "generated_at", "valid_from", "valid_to", "metadata", "model"]


class CellPredictionSerializer(serializers.ModelSerializer):
    cell_code = serializers.CharField(source="cell.code", read_only=True)
    geometry = serializers.JSONField(source="cell.geometry", read_only=True)
    centroid = serializers.JSONField(source="cell.centroid", read_only=True)

    class Meta:
        model = CellPrediction
        fields = ["id", "cell_code", "geometry", "centroid", "predicted_lst_c"]
