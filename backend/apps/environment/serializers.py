from __future__ import annotations

from rest_framework import serializers

from .models import EnvironmentalObservation, SatelliteScene


class SatelliteSceneSerializer(serializers.ModelSerializer):
    class Meta:
        model = SatelliteScene
        fields = [
            "id",
            "scene_id",
            "platform",
            "collection",
            "acquired_at",
            "cloud_cover_pct",
            "processing_level",
            "bounds",
            "source_url",
            "metadata",
        ]


class EnvironmentalObservationSerializer(serializers.ModelSerializer):
    cell_code = serializers.CharField(source="cell.code", read_only=True)
    scene_id = serializers.CharField(source="scene.scene_id", read_only=True)

    class Meta:
        model = EnvironmentalObservation
        fields = [
            "id",
            "cell_code",
            "scene_id",
            "observed_on",
            "lst_c",
            "ndvi",
            "ndbi",
            "mndwi",
            "valid_pixel_count",
            "valid_pixel_fraction",
            "quality_flags",
            "processing_version",
        ]
