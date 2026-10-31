"""Community report ingestion, image sanitisation, duplicate hints and moderation."""

from __future__ import annotations

import hashlib
import io
import logging
from collections import Counter
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

from .models import (
    REPORT_LIFETIME_HOURS,
    RESIDENT_CLEARS_REQUIRED,
    ConfirmationKind,
    IncidentAttachment,
    IncidentCategory,
    IncidentConfirmation,
    IncidentReport,
    IncidentStatus,
    IncidentStatusHistory,
)

logger = logging.getLogger("apps.incidents")

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
MIN_IMAGE_EDGE = 200
MAX_IMAGE_EDGE = 6000
MAX_IMAGE_PIXELS = 24_000_000
DUPLICATE_RADIUS_M = 250
DUPLICATE_WINDOW = timedelta(hours=6)
NEAREST_NEIGHBOURHOOD_KM = 3
MAX_LIFETIME_MULTIPLE = 4
LIVE_MAP_LIMIT = 500
HISTORY_WINDOW = timedelta(days=365)
RECURRING_MIN_DAYS = 2
RECURRING_CATEGORIES = {IncidentCategory.WATERLOGGING, IncidentCategory.FLOODING}
NOT_LIVE_STATUSES = {
    IncidentStatus.RESOLVED,
    IncidentStatus.REJECTED,
    IncidentStatus.DUPLICATE,
    IncidentStatus.EXPIRED,
}

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


def report_lifetime(category: str) -> timedelta:
    return timedelta(hours=REPORT_LIFETIME_HOURS[category])


def nearest_neighbourhood(area: Area, latitude: float, longitude: float) -> Neighbourhood | None:
    """The closest published locality, used to name a report. Not an address lookup."""
    closest, closest_m = None, NEAREST_NEIGHBOURHOOD_KM * 1000
    for item in Neighbourhood.objects.filter(area=area, is_active=True):
        distance = haversine_m(latitude, longitude, item.latitude, item.longitude)
        if distance <= closest_m:
            closest, closest_m = item, distance
    return closest


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
        width, height = probe.size
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValidationError({"attachments": "One of the uploaded files is not a valid image."}) from exc

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError({"attachments": "Only JPEG, PNG or WebP images are accepted."})

    # Checked from the header, before any pixels are decoded into memory.
    if width < MIN_IMAGE_EDGE or height < MIN_IMAGE_EDGE:
        raise ValidationError(
            {"attachments": f"Images must be at least {MIN_IMAGE_EDGE}x{MIN_IMAGE_EDGE} pixels."}
        )
    if width > MAX_IMAGE_EDGE or height > MAX_IMAGE_EDGE or width * height > MAX_IMAGE_PIXELS:
        raise ValidationError({"attachments": "Image dimensions are too large; maximum is 6000x6000."})

    try:
        upload.seek(0)
        image = Image.open(upload)
        image = ImageOps.exif_transpose(image)
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ValidationError({"attachments": "One of the uploaded images could not be read."}) from exc

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


def _create_attachment(
    incident: IncidentReport, upload, cleaned: tuple[bytes, str, int, int]
) -> IncidentAttachment:
    data, content_type, width, height = cleaned
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
    occurred_at,
    latitude: float,
    longitude: float,
    description: str = "",
    water_depth: str = "",
    passability: str = "",
    location_accuracy_m: float | None = None,
    address_text: str = "",
    neighbourhood: Neighbourhood | None = None,
    attachments: list | None = None,
) -> IncidentReport:
    # Validate every image first: rolling back the transaction cannot remove files.
    cleaned_images = [(upload, _clean_image(upload)) for upload in attachments or []]
    incident = IncidentReport(
        reporter=reporter,
        area=area,
        neighbourhood=neighbourhood or nearest_neighbourhood(area, latitude, longitude),
        category=category,
        description=description.strip(),
        occurred_at=occurred_at,
        water_depth=water_depth,
        passability=passability,
        location_accuracy_m=location_accuracy_m,
        expires_at=occurred_at + report_lifetime(category),
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
    for upload, cleaned in cleaned_images:
        _create_attachment(incident, upload, cleaned)
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


def live_reports(area: Area, *, category: str | None = None, now=None) -> list:
    """Public reports that are still believed to be current, newest first."""
    queryset = (
        IncidentReport.objects.filter(
            area=area.data_area,
            is_public=True,
            cleared_at__isnull=True,
            expires_at__gt=now or timezone.now(),
        )
        .exclude(status__in=NOT_LIVE_STATUSES)
        .select_related("neighbourhood")
        .prefetch_related("confirmations")
        .order_by("-occurred_at")
    )
    if category:
        queryset = queryset.filter(category=category)
    reports = queryset[:LIVE_MAP_LIMIT]
    if area != area.data_area:
        return [report for report in reports if area.covers(report.latitude, report.longitude)]
    return list(reports)


def report_history(area: Area, *, neighbourhood: Neighbourhood | None = None, now=None) -> dict:
    """Patterns drawn only from real public reports. With no reports, every list is empty."""
    now = now or timezone.now()
    reports = (
        IncidentReport.objects.filter(
            area=area.data_area, is_public=True, occurred_at__gte=now - HISTORY_WINDOW
        )
        .exclude(status__in=[IncidentStatus.REJECTED, IncidentStatus.DUPLICATE])
        .select_related("neighbourhood")
    )
    if neighbourhood:
        reports = reports.filter(neighbourhood=neighbourhood)

    by_category: Counter = Counter()
    by_month: Counter = Counter()
    spots: dict[str, dict] = {}
    for report in reports:
        if area != area.data_area and not area.covers(report.latitude, report.longitude):
            continue
        by_category[report.get_category_display()] += 1
        by_month[report.occurred_at.strftime("%Y-%m")] += 1
        if report.category in RECURRING_CATEGORIES and report.neighbourhood:
            spot = spots.setdefault(
                report.neighbourhood.slug,
                {"name": report.neighbourhood.name, "slug": report.neighbourhood.slug, "reports": 0, "days": set()},
            )
            spot["reports"] += 1
            spot["days"].add(report.occurred_at.date())

    recurring = sorted(
        (
            {"name": spot["name"], "slug": spot["slug"], "reports": spot["reports"], "days": len(spot["days"])}
            for spot in spots.values()
            if len(spot["days"]) >= RECURRING_MIN_DAYS
        ),
        key=lambda spot: (-spot["days"], -spot["reports"]),
    )
    return {
        "window_days": HISTORY_WINDOW.days,
        "total": sum(by_category.values()),
        "by_category": dict(by_category.most_common()),
        "by_month": dict(sorted(by_month.items())),
        "recurring_water_spots": recurring[:10],
        "note": "Counts of resident reports, which depend on who is using the platform. Not official records.",
    }


@transaction.atomic
def record_confirmation(incident: IncidentReport, *, user, kind: str) -> IncidentReport:
    """Store a resident's vote, then extend or end the report's time on the map."""
    incident = IncidentReport.objects.select_for_update().get(pk=incident.pk)
    if not incident.is_active or incident.status in NOT_LIVE_STATUSES:
        raise ValidationError({"kind": "This report is no longer active."})
    is_reporter = incident.reporter_id == user.id
    if is_reporter and kind != ConfirmationKind.CLEARED:
        raise ValidationError({"kind": "Another resident needs to confirm your report."})

    IncidentConfirmation.objects.update_or_create(incident=incident, user=user, defaults={"kind": kind})
    now = timezone.now()

    if kind == ConfirmationKind.STILL_THERE:
        lifetime = report_lifetime(incident.category)
        latest_allowed = incident.occurred_at + lifetime * MAX_LIFETIME_MULTIPLE
        incident.expires_at = max(incident.expires_at, min(now + lifetime, latest_allowed))
        incident.save(update_fields=["expires_at", "updated_at"])
    elif kind == ConfirmationKind.CLEARED:
        clears = incident.confirmations.filter(kind=ConfirmationKind.CLEARED).exclude(
            user_id=incident.reporter_id
        )
        if is_reporter or getattr(user, "is_moderator", False) or clears.count() >= RESIDENT_CLEARS_REQUIRED:
            incident.cleared_at = now
            incident.expires_at = now
            incident.save(update_fields=["cleared_at", "expires_at", "updated_at"])

    logger.info("Report confirmation recorded", extra={"incident_id": str(incident.id), "kind": kind})
    return incident


def find_potential_duplicates(incident: IncidentReport, *, user=None, limit: int = 3) -> list[dict]:
    """Nearby reports the user may see, same category, short window. Never auto-merges."""
    min_lat, min_lon, max_lat, max_lon = bbox_around_point(
        incident.latitude, incident.longitude, DUPLICATE_RADIUS_M
    )
    nearby = IncidentReport.objects.filter(
        area=incident.area,
        category=incident.category,
        latitude__gte=min_lat,
        latitude__lte=max_lat,
        longitude__gte=min_lon,
        longitude__lte=max_lon,
        occurred_at__gte=incident.occurred_at - DUPLICATE_WINDOW,
        occurred_at__lte=incident.occurred_at + DUPLICATE_WINDOW,
    )
    candidates = (
        visible_incidents(nearby, user)
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
        incident.cleared_at = now
        incident.expires_at = now
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
