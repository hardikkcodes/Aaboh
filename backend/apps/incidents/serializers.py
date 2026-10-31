from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.core.geometry import parse_geometry, point_geojson
from apps.core.serializers import source_summary
from apps.locations.models import Area, Neighbourhood

from .models import (
    IncidentAttachment,
    IncidentCategory,
    IncidentReport,
    IncidentStatus,
    IncidentStatusHistory,
)

MAX_ATTACHMENTS = 4
MIN_DESCRIPTION_LENGTH = 10
MAX_AGE = timedelta(days=7)
MAX_FUTURE = timedelta(minutes=30)


def verification_state(status: str) -> str:
    """Public-facing verification wording that never overstates a community report."""
    if status in {IncidentStatus.SUBMITTED, IncidentStatus.UNDER_REVIEW}:
        return "UNVERIFIED"
    if status in {IncidentStatus.VERIFIED, IncidentStatus.RESOLVED}:
        return "VERIFIED"
    return status


class IncidentAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = IncidentAttachment
        fields = ["id", "url", "content_type", "size_bytes", "created_at"]

    def get_url(self, obj) -> str:
        request = self.context.get("request")
        url = obj.file.url
        return request.build_absolute_uri(url) if request else url


class IncidentStatusHistorySerializer(serializers.ModelSerializer):
    from_status_label = serializers.SerializerMethodField()
    to_status_label = serializers.SerializerMethodField()

    class Meta:
        model = IncidentStatusHistory
        fields = [
            "id",
            "from_status",
            "from_status_label",
            "to_status",
            "to_status_label",
            "note",
            "created_at",
        ]

    def get_from_status_label(self, obj) -> str:
        return dict(IncidentStatus.choices).get(obj.from_status, obj.from_status)

    def get_to_status_label(self, obj) -> str:
        return dict(IncidentStatus.choices).get(obj.to_status, obj.to_status)


class IncidentListSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    verification_state = serializers.SerializerMethodField()
    area = serializers.SerializerMethodField()
    neighbourhood = serializers.SerializerMethodField()
    attachments_count = serializers.IntegerField(source="attachments.count", read_only=True)
    is_owner = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()

    class Meta:
        model = IncidentReport
        fields = [
            "id",
            "category",
            "category_label",
            "description",
            "occurred_at",
            "status",
            "status_label",
            "verification_state",
            "latitude",
            "longitude",
            "point",
            "address_text",
            "area",
            "neighbourhood",
            "is_public",
            "verified_at",
            "resolved_at",
            "attachments_count",
            "is_owner",
            "created_at",
            "updated_at",
            "source",
        ]

    def get_verification_state(self, obj) -> str:
        return verification_state(obj.status)

    def get_area(self, obj) -> dict:
        return {"slug": obj.area.slug, "name": obj.area.name}

    def get_neighbourhood(self, obj) -> dict | None:
        if not obj.neighbourhood:
            return None
        return {"slug": obj.neighbourhood.slug, "name": obj.neighbourhood.name}

    def get_is_owner(self, obj) -> bool:
        request = self.context.get("request")
        user = self.context.get("user") or getattr(request, "user", None)
        return bool(user and user.is_authenticated and obj.reporter_id == user.id)

    def get_source(self, obj) -> dict:
        return source_summary(obj.source)


class IncidentDetailSerializer(IncidentListSerializer):
    attachments = IncidentAttachmentSerializer(many=True, read_only=True)
    status_history = IncidentStatusHistorySerializer(many=True, read_only=True)
    moderation_note = serializers.SerializerMethodField()
    potential_duplicates = serializers.SerializerMethodField()

    class Meta(IncidentListSerializer.Meta):
        fields = IncidentListSerializer.Meta.fields + [
            "attachments",
            "status_history",
            "moderation_note",
            "potential_duplicates",
        ]

    def get_potential_duplicates(self, obj) -> list[dict]:
        from .services import find_potential_duplicates

        return find_potential_duplicates(obj)

    def get_moderation_note(self, obj) -> str:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated and (
            getattr(user, "is_moderator", False) or obj.reporter_id == user.id
        ):
            return obj.moderation_note
        return ""


class IncidentCreateSerializer(serializers.Serializer):
    area = serializers.SlugRelatedField(slug_field="slug", queryset=Area.objects.filter(is_active=True))
    neighbourhood = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Neighbourhood.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    category = serializers.ChoiceField(choices=IncidentCategory.choices)
    description = serializers.CharField(max_length=2000, trim_whitespace=True)
    occurred_at = serializers.DateTimeField()
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
    address_text = serializers.CharField(max_length=200, required=False, allow_blank=True)
    attachments = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        allow_empty=True,
        max_length=MAX_ATTACHMENTS,
        write_only=True,
    )

    def validate_description(self, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < MIN_DESCRIPTION_LENGTH:
            raise serializers.ValidationError(
                f"Describe what you observed in at least {MIN_DESCRIPTION_LENGTH} characters."
            )
        return value

    def validate_occurred_at(self, value):
        now = timezone.now()
        if value > now + MAX_FUTURE:
            raise serializers.ValidationError("Occurrence time cannot be in the future.")
        if value < now - MAX_AGE:
            raise serializers.ValidationError("Reports older than 7 days cannot be submitted.")
        return value

    def validate_address_text(self, value: str) -> str:
        value = value.strip()
        if "@" in value or any(ch.isdigit() for ch in value) and len(value) > 120:
            raise serializers.ValidationError(
                "Use a coarse landmark description only. Do not enter a house number or contact details."
            )
        return value

    def validate(self, attrs):
        area: Area = attrs["area"]
        neighbourhood = attrs.get("neighbourhood")
        if neighbourhood and neighbourhood.area_id != area.id:
            raise serializers.ValidationError(
                {"neighbourhood": "This neighbourhood does not belong to the selected area."}
            )
        point = parse_geometry(point_geojson(attrs["latitude"], attrs["longitude"]))
        if area.boundary and not parse_geometry(area.boundary).covers(point):
            raise serializers.ValidationError(
                {"latitude": "Report location is outside the selected area boundary."}
            )
        attachments = attrs.get("attachments") or []
        if len(attachments) > MAX_ATTACHMENTS:
            raise serializers.ValidationError(
                {"attachments": f"At most {MAX_ATTACHMENTS} images may be attached."}
            )
        return attrs

    def create(self, validated_data):
        from .services import create_incident

        request = self.context["request"]
        attachments = validated_data.pop("attachments", [])
        return create_incident(
            reporter=request.user,
            attachments=attachments,
            **validated_data,
        )


class IncidentEditSerializer(serializers.ModelSerializer):
    neighbourhood = serializers.SlugRelatedField(
        slug_field="slug",
        queryset=Neighbourhood.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = IncidentReport
        fields = ["category", "description", "occurred_at", "address_text", "neighbourhood"]

    def validate_description(self, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < MIN_DESCRIPTION_LENGTH:
            raise serializers.ValidationError(
                f"Describe what you observed in at least {MIN_DESCRIPTION_LENGTH} characters."
            )
        return value

    def validate_occurred_at(self, value):
        now = timezone.now()
        if value > now + MAX_FUTURE:
            raise serializers.ValidationError("Occurrence time cannot be in the future.")
        if value < now - MAX_AGE:
            raise serializers.ValidationError("Occurrence time is too old for an editable report.")
        return value

    def validate_neighbourhood(self, value):
        if value and self.instance and value.area_id != self.instance.area_id:
            raise serializers.ValidationError("This neighbourhood does not belong to the report area.")
        return value


class IncidentModerationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=IncidentStatus.choices)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
    duplicate_of = serializers.UUIDField(required=False, allow_null=True)
    is_public = serializers.BooleanField(required=False)

    def validate(self, attrs):
        from .services import validate_transition

        incident = self.context["incident"]
        to_status = attrs["status"]
        duplicate_id = attrs.get("duplicate_of")
        duplicate = None
        if duplicate_id:
            try:
                duplicate = IncidentReport.objects.get(pk=duplicate_id)
            except IncidentReport.DoesNotExist as exc:
                raise serializers.ValidationError({"duplicate_of": "Duplicate report not found."}) from exc
            if duplicate.pk == incident.pk:
                raise serializers.ValidationError({"duplicate_of": "A report cannot duplicate itself."})
        validate_transition(incident.status, to_status, duplicate=duplicate)
        attrs["duplicate"] = duplicate
        return attrs


class IncidentStatusHistoryPublicSerializer(serializers.ModelSerializer):
    from_status_label = serializers.SerializerMethodField()
    to_status_label = serializers.SerializerMethodField()

    class Meta:
        model = IncidentStatusHistory
        fields = ["from_status", "from_status_label", "to_status", "to_status_label", "note", "created_at"]

    def get_from_status_label(self, obj) -> str:
        return dict(IncidentStatus.choices).get(obj.from_status, obj.from_status)

    def get_to_status_label(self, obj) -> str:
        return dict(IncidentStatus.choices).get(obj.to_status, obj.to_status)
