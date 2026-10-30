"""Community report ingestion, image sanitisation, duplicate hints and moderation."""

from __future__ import annotations

import hashlib
import io
import logging
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

from apps.core.geometry import bbox_around_point, haversine_m, parse_geometry, point_geojson
from apps.core.models import DataSource
from apps.locations.models import Area, Neighbourhood

from .models import IncidentAttachment, IncidentReport, IncidentStatus, IncidentStatusHistory

logger = logging.getLogger("apps.incidents")

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MIN_IMAGE_EDGE = 200
MAX_IMAGE_EDGE = 6000
MAX_IMAGE_PIXELS = 24_000_000
DUPLICATE_RADIUS_M = 250
DUPLICATE_WINDOW = timedelta(hours=6)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    IncidentStatus.SUBMITTED: {
        IncidentStatus.UNDER_REVIEW,
        IncidentStatus.VERIFIED,
        IncidentStatus.REJECTED,
        IncidentStatus.DUPLICATE,
        IncidentStatus.EXPIRED,
    },
    IncidentStatus.UNDER_REVIEW: {
        IncidentStatus.VERIFIED,
        IncidentStatus.REJECTED,
        IncidentStatus.DUPLICATE,
        IncidentStatus.EXPIRED,
    },
    IncidentStatus.VERIFIED: {
        IncidentStatus.RESOLVED,
        IncidentStatus.EXPIRED,
    },
    IncidentStatus.RESOLVED: set(),
    IncidentStatus.REJECTED: {IncidentStatus.UNDER_REVIEW},
    IncidentStatus.EXPIRED: {IncidentStatus.UNDER_REVIEW},
    IncidentStatus.DUPLICATE: {IncidentStatus.UNDER_REVIEW},
}


def community_source() -> DataSource:
    return DataSource.objects.get(slug="community_reports")


def _clean_image(upload) -> tuple[bytes, str, int, int]:
    """Validate, orient, strip metadata and re-encode an uploaded image as JPEG."""
    max_bytes = settings.INCIDENT_IMAGE_MAX_BYTES
    if upload.size > max_bytes:
        raise ValidationError(
            {"attachments": f"Each image must be {max_bytes // (1024 * 1024)} MB or smaller."}
        )
    if upload.size == 0:
        raise ValidationError({"attachments": "An uploaded image is empty."})

    try:
        upload.seek(0)
        probe = Image.open(upload)
        probe.verify()
        image_format = (probe.format or "").upper()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError({"attachments": "One of the uploaded files is not a valid image."}) from exc

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError({"attachments": "Only JPEG, PNG or WebP images are accepted."})

    try:
        upload.seek(0)
        image = Image.open(upload)
        image = ImageOps.exif_transpose(image)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError({"attachments": "One of the uploaded images could not be read."}) from exc

    width, height = image.size
    if width < MIN_IMAGE_EDGE or height < MIN_IMAGE_EDGE:
        raise ValidationError(
            {"attachments": f"Images must be at least {MIN_IMAGE_EDGE}x{MIN_IMAGE_EDGE} pixels."}
        )
    if width > MAX_IMAGE_EDGE or height > MAX_IMAGE_EDGE or width * height > MAX_IMAGE_PIXELS:
        raise ValidationError({"attachments": "Image dimensions are too large; maximum is 6000x6000."})

    image.thumbnail((4000, 4000), Image.Resampling.LANCZOS)
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=85, optimize=True)
    return output.getvalue(), "image/jpeg", image.width, image.height


def _create_attachment(incident: IncidentReport, upload) -> IncidentAttachment:
    data, content_type, width, height = _clean_image(upload)
    sha256 = hashlib.sha256(data).hexdigest()
    name = f"{sha256[:16]}.jpg"
    attachment = IncidentAttachment(
        incident=incident,
        original_name=Path(upload.name or "image").name[:200],
        content_type=content_type,
        size_bytes=len(data),
        sha256=sha256,
    )
    attachment.file.save(name, ContentFile(data), save=False)
    attachment.save()
    logger.info(
        "Incident attachment stored",
        extra={"incident_id": str(incident.id), "bytes": len(data), "width": width, "height": height},
    )
    return attachment


@transaction.atomic
def create_incident(
    *,
    reporter,
    area: Area,
    category: str,
    description: str,
    occurred_at,
    latitude: float,
    longitude: float,
    address_text: str = "",
    neighbourhood: Neighbourhood | None = None,
    attachments: list | None = None,
) -> IncidentReport:
    incident = IncidentReport(
        reporter=reporter,
        area=area,
        neighbourhood=neighbourhood,
        category=category,
        description=description.strip(),
        occurred_at=occurred_at,
        point=point_geojson(latitude, longitude),
        latitude=latitude,
        longitude=longitude,
        address_text=address_text.strip(),
        status=IncidentStatus.SUBMITTED,
        source=community_source(),
    )
    try:
        incident.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc
    incident.save()
    IncidentStatusHistory.objects.create(
        incident=incident,
        from_status="",
        to_status=IncidentStatus.SUBMITTED,
        changed_by=reporter,
        note="Report submitted by community member.",
    )
    for upload in attachments or []:
        _create_attachment(incident, upload)
    logger.info(
        "Community incident created",
        extra={"incident_id": str(incident.id), "area": area.slug, "category": category},
    )
    return incident


def visible_incidents(queryset, user):
    """Apply public visibility rules for reads."""
    if user and user.is_authenticated and getattr(user, "is_moderator", False):
        return queryset
    if user and user.is_authenticated:
        from django.db.models import Q

        return queryset.filter(Q(is_public=True) | Q(reporter=user))
    return queryset.filter(is_public=True)


def find_potential_duplicates(incident: IncidentReport, *, limit: int = 3) -> list[dict]:
    """Nearby reports of the same category within a short window. Never auto-merges."""
    min_lat, min_lon, max_lat, max_lon = bbox_around_point(
        incident.latitude, incident.longitude, DUPLICATE_RADIUS_M
    )
    candidates = (
        IncidentReport.objects.filter(
            area=incident.area,
            category=incident.category,
            latitude__gte=min_lat,
            latitude__lte=max_lat,
            longitude__gte=min_lon,
            longitude__lte=max_lon,
            occurred_at__gte=incident.occurred_at - DUPLICATE_WINDOW,
            occurred_at__lte=incident.occurred_at + DUPLICATE_WINDOW,
        )
        .exclude(pk=incident.pk)
        .exclude(status__in=[IncidentStatus.REJECTED, IncidentStatus.DUPLICATE])
        .order_by("-created_at")[:12]
    )
    results = []
    for candidate in candidates:
        distance = haversine_m(
            incident.latitude,
            incident.longitude,
            candidate.latitude,
            candidate.longitude,
        )
        if distance > DUPLICATE_RADIUS_M:
            continue
        results.append(
            {
                "id": str(candidate.id),
                "category": candidate.category,
                "status": candidate.status,
                "verification_state": "VERIFIED"
                if candidate.status in {IncidentStatus.VERIFIED, IncidentStatus.RESOLVED}
                else "UNVERIFIED"
                if candidate.status in {IncidentStatus.SUBMITTED, IncidentStatus.UNDER_REVIEW}
                else candidate.status,
                "occurred_at": candidate.occurred_at,
                "distance_m": round(distance, 1),
                "created_at": candidate.created_at,
            }
        )
        if len(results) >= limit:
            break
    results.sort(key=lambda item: item["distance_m"])
    return results


def validate_transition(from_status: str, to_status: str, *, duplicate: IncidentReport | None = None) -> None:
    if from_status == to_status:
        raise ValidationError({"status": "The report already has this status."})
    allowed = ALLOWED_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise ValidationError(
            {"status": f"Cannot move a report from {from_status} to {to_status}."}
        )
    if to_status == IncidentStatus.DUPLICATE and duplicate is None:
        raise ValidationError({"duplicate_of": "A duplicate must reference the original report."})
    if to_status != IncidentStatus.DUPLICATE and duplicate is not None:
        raise ValidationError(
            {"duplicate_of": "duplicate_of may only be supplied when marking a report as DUPLICATE."}
        )


@transaction.atomic
def moderate_incident(
    incident: IncidentReport,
    *,
    moderator,
    to_status: str,
    note: str = "",
    duplicate: IncidentReport | None = None,
    is_public: bool | None = None,
) -> IncidentReport:
    validate_transition(incident.status, to_status, duplicate=duplicate)
    from_status = incident.status
    now = timezone.now()
    incident.status = to_status
    incident.moderation_note = note.strip()[:500]

    if to_status == IncidentStatus.VERIFIED:
        incident.verified_by = moderator
        incident.verified_at = now
    if to_status == IncidentStatus.RESOLVED:
        incident.resolved_at = now
    if to_status == IncidentStatus.DUPLICATE:
        incident.duplicate_of = duplicate
        incident.is_public = False if is_public is None else is_public
    if is_public is not None:
        incident.is_public = is_public
    if to_status in {IncidentStatus.REJECTED, IncidentStatus.EXPIRED}:
        incident.is_public = False if is_public is None else is_public

    incident.save()
    IncidentStatusHistory.objects.create(
        incident=incident,
        from_status=from_status,
        to_status=to_status,
        changed_by=moderator,
        note=note.strip()[:500],
    )
    logger.info(
        "Incident moderated",
        extra={"incident_id": str(incident.id), "from": from_status, "to": to_status},
    )
    return incident


def incident_contains_point(incident: IncidentReport, lat: float, lon: float) -> bool:
    return parse_geometry(incident.point).covers(parse_geometry(point_geojson(lat, lon)))
