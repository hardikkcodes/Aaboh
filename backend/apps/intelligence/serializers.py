from __future__ import annotations

from rest_framework import serializers

from apps.core.serializers import source_summary

from .models import Recommendation, RecommendationEvidence


class RecommendationEvidenceSerializer(serializers.ModelSerializer):
    source = serializers.SerializerMethodField()

    class Meta:
        model = RecommendationEvidence
        fields = [
            "id",
            "evidence_type",
            "label",
            "source",
            "observed_at",
            "reference",
            "source_url",
            "quality_status",
        ]

    def get_source(self, obj) -> dict:
        return source_summary(obj.source)


class RecommendationSerializer(serializers.ModelSerializer):
    area = serializers.SerializerMethodField()
    severity_label = serializers.CharField(source="get_severity_display", read_only=True)
    evidence = RecommendationEvidenceSerializer(many=True, read_only=True)

    class Meta:
        model = Recommendation
        fields = [
            "id",
            "area",
            "rule_id",
            "kind",
            "title",
            "body",
            "severity",
            "severity_label",
            "valid_from",
            "valid_until",
            "generated_at",
            "metadata",
            "evidence",
        ]

    def get_area(self, obj) -> dict:
        return {"slug": obj.area.slug, "name": obj.area.name}
