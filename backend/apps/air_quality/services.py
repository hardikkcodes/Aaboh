from __future__ import annotations

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from data_pipelines.providers import open_meteo
from data_pipelines.providers.cpcb import CPCBClient, normalize_records
from django.conf import settings
from django.utils import timezone

from apps.core.models import DataSource, IngestionRun, IngestionRunStatus
from apps.core.quality import DataState
from apps.locations.models import Area

from .models import AirForecastHour, AQIMeasurement, AQIStation

logger = logging.getLogger("apps.air_quality.ingestion")
IST = ZoneInfo("Asia/Kolkata")

MEASUREMENT_FIELDS = ("pm25", "pm10", "no2", "so2", "co", "o3", "nh3")


class AirQualityIngestionError(Exception):
    pass


def ingest_air_forecast(area: Area) -> dict:
    source = DataSource.objects.get(slug="cams_air")
    run = IngestionRun.objects.create(
        source=source, status=IngestionRunStatus.RUNNING, params={"area": area.slug}
    )
    try:
        hourly = open_meteo.fetch_air_forecast(*area.focus).get("hourly") or {}
        retrieved_at = timezone.now()
        written = 0
        for valid_time, pm25, pm10 in zip(hourly["time"], hourly["pm2_5"], hourly["pm10"], strict=True):
            AirForecastHour.objects.update_or_create(
                area=area,
                valid_time=datetime.fromisoformat(valid_time).replace(tzinfo=IST),
                defaults={"source": source, "retrieved_at": retrieved_at, "pm25": pm25, "pm10": pm10},
            )
            written += 1
        AirForecastHour.objects.filter(area=area, valid_time__lt=retrieved_at - timedelta(days=2)).delete()
        run.status = IngestionRunStatus.SUCCESS
        run.records_fetched = run.records_written = written
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "records_fetched", "records_written", "finished_at"])
        return {"written": written, "run_id": str(run.id)}
    except Exception as exc:  # noqa: BLE001 - record every failure so a run never stays RUNNING
        run.status = IngestionRunStatus.FAILED
        run.finished_at = timezone.now()
        run.error_message = str(exc)[:2000]
        run.save(update_fields=["status", "finished_at", "error_message"])
        logger.warning("Air forecast ingestion unavailable: %s", exc)
        raise AirQualityIngestionError(str(exc)) from exc


def ingest_cpcb(
    *,
    max_pages: int = 5,
    page_size: int = 1000,
    cities: list[str] | None = None,
) -> dict:
    source = DataSource.objects.get(slug="cpcb")
    city_filters = [city for city in (cities or []) if city]
    run = IngestionRun.objects.create(
        source=source,
        status=IngestionRunStatus.RUNNING,
        params={
            "provider": "cpcb",
            "max_pages": max_pages,
            "page_size": page_size,
            "cities": city_filters or None,
        },
    )
    try:
        client = CPCBClient(
            api_key=settings.CPCB_API_KEY,
            resource_id=settings.CPCB_RESOURCE_ID,
            base_url=settings.CPCB_BASE_URL,
            timeout=settings.CPCB_TIMEOUT,
        )
        rows: list[dict] = []
        seen_rows: set[str] = set()
        for city in city_filters or [None]:
            page = 0
            city_rows = 0
            while page < max_pages:
                payload = client.fetch_page(limit=page_size, offset=page * page_size, city=city)
                batch = payload.get("records") or []
                city_rows += len(batch)
                for row in batch:
                    key = repr(sorted(row.items())) if isinstance(row, dict) else repr(row)
                    if key in seen_rows:
                        continue
                    seen_rows.add(key)
                    rows.append(row)
                total = int(payload.get("total") or 0)
                page += 1
                if not batch or city_rows >= total:
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
                    "metadata": {
                        "source_rows": len(record["raw"]["rows"]),
                        "aqi_basis": record["raw"].get("aqi_basis"),
                        "pollutant_units": record["pollutant_units"],
                    },
                },
            )
            stations_written += int(created)
            pollutants = {field: record["pollutants"].get(field) for field in MEASUREMENT_FIELDS}
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
                    "raw": {
                        "rows": record["raw"]["rows"],
                        "units": record["pollutant_units"],
                        "aqi_basis": record["raw"].get("aqi_basis"),
                    },
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
            "cities": city_filters,
            "run_id": str(run.id),
        }
    except Exception as exc:  # noqa: BLE001 - record every failure so a run never stays RUNNING
        run.status = IngestionRunStatus.FAILED
        run.finished_at = timezone.now()
        run.error_message = str(exc)[:2000]
        run.save(update_fields=["status", "finished_at", "error_message"])
        logger.warning("CPCB ingestion unavailable: %s", exc)
        raise AirQualityIngestionError(str(exc)) from exc
