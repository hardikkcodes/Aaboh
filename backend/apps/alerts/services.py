from __future__ import annotations

import logging

from data_pipelines.providers.imd import IMDClient, IMDNotConfigured, IMDProviderError, normalize_warnings
from django.conf import settings
from django.utils import timezone

from apps.core.models import DataSource, IngestionRun, IngestionRunStatus

from .models import OfficialAlert

logger = logging.getLogger("apps.alerts.ingestion")


class AlertIngestionError(Exception):
    pass


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
        written = 0
        for record in records:
            _, created = OfficialAlert.objects.update_or_create(
                source=source,
                external_id=record["external_id"],
                defaults={**{k: v for k, v in record.items() if k != "external_id"}, "status": "active"},
            )
            written += int(created)

        # Mark alerts whose validity has elapsed.
        OfficialAlert.objects.filter(
            source=source, status="active", expires_at__lt=timezone.now()
        ).update(status="expired")

        run.status = IngestionRunStatus.SUCCESS
        run.records_fetched = len(records)
        run.records_written = written
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "records_fetched", "records_written", "finished_at"])
        return {"fetched": len(records), "written": written, "run_id": str(run.id)}
    except (IMDNotConfigured, IMDProviderError) as exc:
        run.status = IngestionRunStatus.FAILED
        run.finished_at = timezone.now()
        run.error_message = str(exc)[:2000]
        run.save(update_fields=["status", "finished_at", "error_message"])
        logger.warning("IMD alert ingestion unavailable: %s", exc)
        raise AlertIngestionError(str(exc)) from exc
