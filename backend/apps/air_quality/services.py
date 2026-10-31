from __future__ import annotations

import logging

from data_pipelines.providers.cpcb import (
    CPCBClient,
    CPCBNotConfigured,
    CPCBProviderError,
    normalize_records,
)
from django.conf import settings
from django.utils import timezone

from apps.core.models import DataSource, IngestionRun, IngestionRunStatus
from apps.core.quality import DataState

from .models import AQIMeasurement, AQIStation

logger = logging.getLogger("apps.air_quality.ingestion")


class AirQualityIngestionError(Exception):
    pass


def ingest_cpcb(*, max_pages: int = 5, page_size: int = 1000) -> dict:
    source = DataSource.objects.get(slug="cpcb")
    run = IngestionRun.objects.create(
        source=source,
        status=IngestionRunStatus.RUNNING,
        params={"provider": "cpcb", "max_pages": max_pages, "page_size": page_size},
    )
    try:
        client = CPCBClient(
            api_key=settings.CPCB_API_KEY,
            resource_id=settings.CPCB_RESOURCE_ID,
            base_url=settings.CPCB_BASE_URL,
            timeout=settings.CPCB_TIMEOUT,
        )
        rows: list[dict] = []
        page = 0
        while page < max_pages:
            payload = client.fetch_page(limit=page_size, offset=page * page_size)
            batch = payload.get("records") or []
            rows.extend(batch)
            total = int(payload.get("total") or 0)
            page += 1
            if not batch or len(rows) >= total:
                break

        normalized, warnings = normalize_records({"records": rows}, retrieved_at=timezone.now())
        written = 0
        stations_written = 0
        for record in normalized:
            station, created = AQIStation.objects.update_or_create(
                source=source,
                external_id=record["external_id"],
                defaults={
                    "name": record["station"],
                    "city": record["city"],
                    "state": record["state"],
                    "point": {"type": "Point", "coordinates": [record["longitude"], record["latitude"]]},
                    "latitude": record["latitude"],
                    "longitude": record["longitude"],
                    "is_active": True,
                    "metadata": {"source_rows": len(record["raw"]["rows"])},
                },
            )
            stations_written += int(created)
            pollutants = dict(record["pollutants"])
            units = pollutants.pop("units", {})
            AQIMeasurement.objects.update_or_create(
                station=station,
                measured_at=record["measured_at"],
                defaults={
                    "source": source,
                    "retrieved_at": record["retrieved_at"],
                    "aqi": record["aqi"],
                    "aqi_category": record["aqi_category"],
                    "quality_status": DataState.PARTIAL if record["quality_flags"] else DataState.AVAILABLE,
                    "quality_flags": record["quality_flags"],
                    "raw": {"rows": record["raw"]["rows"], "units": units},
                    **pollutants,
                },
            )
            written += 1

        run.records_fetched = len(rows)
        run.records_written = written
        run.finished_at = timezone.now()
        run.status = IngestionRunStatus.SUCCESS if written else IngestionRunStatus.PARTIAL
        if warnings:
            run.error_message = "; ".join(warnings[:8])[:2000]
        run.save(update_fields=["records_fetched", "records_written", "finished_at", "status", "error_message"])
        if not written:
            raise AirQualityIngestionError(
                "CPCB returned no usable station measurements. " + "; ".join(warnings[:3])
            )
        return {
            "rows": len(rows),
            "written": written,
            "stations_created": stations_written,
            "warnings": warnings,
            "run_id": str(run.id),
        }
    except (CPCBNotConfigured, CPCBProviderError, AirQualityIngestionError) as exc:
        run.status = IngestionRunStatus.FAILED
        run.finished_at = timezone.now()
        run.error_message = str(exc)[:2000]
        run.save(update_fields=["status", "finished_at", "error_message"])
        logger.warning("CPCB ingestion unavailable: %s", exc)
        raise AirQualityIngestionError(str(exc)) from exc
