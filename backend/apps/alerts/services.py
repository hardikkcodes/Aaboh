from __future__ import annotations

import logging

from data_pipelines.providers.imd import IMDClient, normalize_warnings
from data_pipelines.providers.sachet import SACHETClient, normalize_alerts
from django.conf import settings
from django.utils import timezone

from apps.core.geometry import parse_geometry
from apps.core.models import DataSource, IngestionRun, IngestionRunStatus
from apps.locations.models import Area

from .models import AlertStatus, OfficialAlert

logger = logging.getLogger("apps.alerts.ingestion")


class AlertMatch:
    NAMED = "named"
    STATE = "state"


class AlertIngestionError(Exception):
    pass


def scope_matches(areas_text: str, terms: list[str] | None = None) -> bool:
    """Whether a published alert area string covers the configured scope."""
    active_terms = [term for term in (terms or settings.SACHET_SCOPE_TERMS) if term]
    return scope_text_matches(areas_text, active_terms)


def scope_text_matches(areas_text: str, terms: list[str]) -> bool:
    text = (areas_text or "").lower()
    return any(term.lower() in text for term in terms if term)


def alert_match(alert: OfficialAlert, area: Area) -> str | None:
    """How an alert relates to an area: named in it, state-wide, or not at all.

    Alert text can be as vague as "9 districts of West Bengal". Dropping those could hide
    a real warning, so they are kept as "state" matches that readers are told to check.
    """
    text = (alert.areas_text or "").lower()
    terms = area.metadata.get("alert_terms") or [area.slug.replace("-", " "), area.name.lower()]
    if any(term in text for term in terms):
        return AlertMatch.NAMED
    if alert.geometry and parse_geometry(alert.geometry).intersects(parse_geometry(area.boundary)):
        return AlertMatch.NAMED
    if any(term in text for term in settings.ALERT_STATE_TERMS):
        return AlertMatch.STATE
    return None


def official_alert_source() -> DataSource | None:
    """The alert source shown to residents.

    SACHET is the key-free public feed and is preferred. IMD remains available
    when it is configured and has been ingested.
    """
    sachet = DataSource.objects.filter(slug="sachet").first()
    if sachet is not None:
        return sachet
    return DataSource.objects.filter(slug="imd").first()


def _upsert_alerts(source: DataSource, records: list[dict]) -> tuple[int, int]:
    created = 0
    updated = 0
    now = timezone.now()
    for record in records:
        payload = {key: value for key, value in record.items() if key != "external_id"}
        payload.setdefault("retrieved_at", now)
        payload["status"] = (
            AlertStatus.ACTIVE
            if payload.get("expires_at") is None or payload["expires_at"] > now
            else AlertStatus.EXPIRED
        )
        _, was_created = OfficialAlert.objects.update_or_create(
            source=source,
            external_id=record["external_id"],
            defaults=payload,
        )
        created += int(was_created)
        updated += int(not was_created)
    return created, updated


def ingest_sachet_alerts(*, scope_terms: list[str] | None = None) -> dict:
    """Ingest the national SACHET feed and record how much of it is in scope.

    Every fetched alert is stored with its original issuing agency so the record
    is auditable. ``in_scope`` counts how many match the configured Kolkata terms;
    zero in-scope alerts is a healthy "no active warning" result, not an outage.
    """
    source = DataSource.objects.get(slug="sachet")
    terms = [term for term in (scope_terms or settings.SACHET_SCOPE_TERMS) if term]
    run = IngestionRun.objects.create(
        source=source,
        status=IngestionRunStatus.RUNNING,
        params={"provider": "sachet", "scope_terms": terms},
    )
    try:
        client = SACHETClient(base_url=settings.SACHET_BASE_URL, timeout=settings.SACHET_TIMEOUT)
        payload = client.fetch_all()
        records = normalize_alerts(payload, retrieved_at=timezone.now())
        created, updated = _upsert_alerts(source, records)

        OfficialAlert.objects.filter(
            source=source, status=AlertStatus.ACTIVE, expires_at__lt=timezone.now()
        ).update(status=AlertStatus.EXPIRED)

        in_scope = [record for record in records if scope_matches(record["areas_text"], terms)]
        run.status = IngestionRunStatus.SUCCESS
        run.records_fetched = len(records)
        run.records_written = created + updated
        run.finished_at = timezone.now()
        run.params = {**run.params, "in_scope": len(in_scope)}
        run.save(update_fields=["status", "records_fetched", "records_written", "finished_at", "params"])
        return {
            "fetched": len(records),
            "written": created,
            "updated": updated,
            "in_scope": len(in_scope),
            "scope_terms": terms,
            "run_id": str(run.id),
        }
    except Exception as exc:  # noqa: BLE001 - record every failure so a run never stays RUNNING
        run.status = IngestionRunStatus.FAILED
        run.finished_at = timezone.now()
        run.error_message = str(exc)[:2000]
        run.save(update_fields=["status", "finished_at", "error_message"])
        logger.warning("SACHET alert ingestion unavailable: %s", exc)
        raise AlertIngestionError(str(exc)) from exc


def ingest_imd_alerts(*, district_id: str | None = None) -> dict:
    source = DataSource.objects.get(slug="imd")
    run = IngestionRun.objects.create(
        source=source,
        status=IngestionRunStatus.RUNNING,
        params={"provider": "imd", "district_id": district_id or None},
    )
    try:
        client = IMDClient(
            api_key=settings.IMD_API_KEY,
            base_url=settings.IMD_BASE_URL,
            api_key_header=settings.IMD_API_KEY_HEADER,
        )
        payload = client.district_warnings(district_id)
        records = normalize_warnings(payload, retrieved_at=timezone.now())
        created, updated = _upsert_alerts(source, records)

        # Mark alerts whose validity has elapsed.
        OfficialAlert.objects.filter(
            source=source, status=AlertStatus.ACTIVE, expires_at__lt=timezone.now()
        ).update(status=AlertStatus.EXPIRED)

        run.status = IngestionRunStatus.SUCCESS
        run.records_fetched = len(records)
        run.records_written = created + updated
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "records_fetched", "records_written", "finished_at"])
        return {
            "fetched": len(records),
            "written": created,
            "updated": updated,
            "run_id": str(run.id),
        }
    except Exception as exc:  # noqa: BLE001 - record every failure so a run never stays RUNNING
        run.status = IngestionRunStatus.FAILED
        run.finished_at = timezone.now()
        run.error_message = str(exc)[:2000]
        run.save(update_fields=["status", "finished_at", "error_message"])
        logger.warning("IMD alert ingestion unavailable: %s", exc)
        raise AlertIngestionError(str(exc)) from exc
