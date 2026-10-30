from __future__ import annotations

from rest_framework import serializers

from apps.core.serializers import source_summary

from .models import OfficialAlert


class OfficialAlertSerializer(serializers.ModelSerializer):
    hazard_label = serializers.CharField(source="get_hazard_display", read_only=True)
    severity_label = serializers.CharField(source="get_severity_display", read_only=True)
    is_current = serializers.BooleanField(read_only=True)
    source = serializers.SerializerMethodField()

    class Meta:
        model = OfficialAlert
        fields = [
            "id",
            "external_id",
            "title",
            "description",
            "hazard",
            "hazard_label",
            "severity",
            "severity_label",
            "certainty",
            "urgency",
            "status",
            "issued_at",
            "effective_at",
            "expires_at",
            "areas_text",
            "geometry",
            "source_url",
            "retrieved_at",
            "quality_status",
            "is_current",
            "source",
        ]

    def get_source(self, obj) -> dict:
        return source_summary(obj.source)
