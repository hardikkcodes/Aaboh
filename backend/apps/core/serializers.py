from __future__ import annotations

from rest_framework import serializers


class SourceSummarySerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    provider_type = serializers.CharField()
    is_official = serializers.BooleanField()
    attribution = serializers.CharField()
    license_name = serializers.CharField()
    spatial_resolution_m = serializers.IntegerField(allow_null=True)
    dataset = serializers.CharField(required=False, allow_blank=True)


def source_summary(source, *, dataset: str = "") -> dict:
    if source is None:
        return {}
    return {
        "slug": source.slug,
        "name": source.name,
        "provider_type": source.provider_type,
        "is_official": source.is_official,
        "attribution": source.attribution,
        "license_name": source.license_name,
        "spatial_resolution_m": source.spatial_resolution_m,
        "dataset": dataset,
    }
