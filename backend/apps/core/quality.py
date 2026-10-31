"""Shared data-quality primitives.

Data state is deliberately separate from data provenance: a provider can be
configured and healthy while the most recent observation is stale.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from django.utils import timezone as dj_timezone

# A run still marked RUNNING after this long crashed without recording a result.
ABANDONED_RUN_AFTER = timedelta(minutes=30)


class DataState:
    AVAILABLE = "AVAILABLE"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"
    PARTIAL = "PARTIAL"
    PROCESSING = "PROCESSING"

    CHOICES = [
        (AVAILABLE, "Available"),
        (STALE, "Stale"),
        (UNAVAILABLE, "Unavailable"),
        (INVALID, "Invalid"),
        (PARTIAL, "Partial"),
        (PROCESSING, "Processing"),
    ]


def utcnow() -> datetime:
    return dj_timezone.now()


def ensure_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if dj_timezone.is_naive(value):
        return value.replace(tzinfo=UTC)
    return value


def freshness_state(
    observed_at: datetime | None,
    *,
    max_age: timedelta | None = None,
    now: datetime | None = None,
) -> str:
    """Classify a single observation by age."""
    observed_at = ensure_aware(observed_at)
    if observed_at is None:
        return DataState.UNAVAILABLE
    if observed_at > (now or utcnow()) + timedelta(minutes=15):
        return DataState.INVALID
    if max_age is None:
        return DataState.AVAILABLE
    return DataState.AVAILABLE if (now or utcnow()) - observed_at <= max_age else DataState.STALE


def max_age_for_source(source) -> timedelta | None:
    minutes = getattr(source, "expected_refresh_minutes", None)
    return timedelta(minutes=minutes) if minutes else None


def source_availability(source) -> dict:
    """Summarise the latest ingestion state for a data source."""
    from .models import IngestionRunStatus

    latest = source.ingestion_runs.order_by("-started_at").first()
    completed = (
        source.ingestion_runs.exclude(status=IngestionRunStatus.RUNNING)
        .order_by("-started_at")
        .first()
    )
    last_success = (
        source.ingestion_runs.filter(status=IngestionRunStatus.SUCCESS)
        .order_by("-finished_at")
        .first()
    )

    success_at = None
    if last_success:
        success_at = last_success.finished_at or last_success.started_at

    running = bool(latest and latest.status == IngestionRunStatus.RUNNING)
    abandoned = running and latest.started_at < utcnow() - ABANDONED_RUN_AFTER
    last_failed = abandoned or bool(completed and completed.status == IngestionRunStatus.FAILED)

    if last_failed:
        state = DataState.STALE if success_at else DataState.UNAVAILABLE
    elif completed and completed.status == IngestionRunStatus.PARTIAL:
        state = DataState.PARTIAL
    elif success_at:
        state = freshness_state(
            success_at,
            max_age=max_age_for_source(source),
        )
    elif running:
        state = DataState.PROCESSING
    else:
        state = DataState.UNAVAILABLE

    # Raw provider errors stay on IngestionRun for operators. This dict reaches
    # public responses, so it must never include them.
    return {
        "state": state,
        "last_success_at": success_at,
        "last_attempt_at": latest.started_at if latest else None,
        "last_attempt_status": latest.status if latest else None,
    }
