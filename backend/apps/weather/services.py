from __future__ import annotations

import logging
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from data_pipelines.normalization.weather import normalize_archive, normalize_forecast
from data_pipelines.providers import open_meteo
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.core.models import DataSource, IngestionRun, IngestionRunStatus
from apps.core.quality import DataState
from apps.locations.models import Area

from .models import WeatherKind, WeatherLocation, WeatherRecord

logger = logging.getLogger("apps.weather.ingestion")
IST = ZoneInfo("Asia/Kolkata")


class WeatherIngestionError(Exception):
    pass


def _source() -> DataSource:
    return DataSource.objects.get(slug="open_meteo")


def _location(area: Area, source: DataSource) -> WeatherLocation:
    latitude = round(area.centroid_lat, 4)
    longitude = round(area.centroid_lon, 4)
    key = f"{latitude:.4f},{longitude:.4f}"
    location, _ = WeatherLocation.objects.get_or_create(
        source=source,
        provider_location_key=key,
        defaults={
            "area": area,
            "name": f"{area.name} (forecast point)",
            "point": {"type": "Point", "coordinates": [longitude, latitude]},
            "latitude": latitude,
            "longitude": longitude,
            "timezone": settings.APP_CONFIG["timezone"],
        },
    )
    return location


def _aware(value: str):
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValueError(f"Invalid provider timestamp: {value}")
    if timezone.is_naive(parsed):
        parsed = parsed.replace(tzinfo=IST)
    return parsed.astimezone(ZoneInfo("UTC"))


def _upsert_records(location: WeatherLocation, source: DataSource, records: list[dict], retrieved_at) -> int:
    written = 0
    for record in records:
        kind = record.pop("kind")
        valid_time = _aware(record.pop("valid_time"))
        raw = record.pop("raw", {})
        payload = dict(record)
        _, created = WeatherRecord.objects.update_or_create(
            location=location,
            source=source,
            kind=kind,
            valid_time=valid_time,
            defaults={
                "retrieved_at": retrieved_at,
                "quality_status": DataState.AVAILABLE,
                "raw": raw,
                **payload,
            },
        )
        written += int(created)
    return written


def ingest_open_meteo(area: Area, *, forecast_days: int = 7) -> dict:
    if not settings.OPEN_METEO_ENABLED:
        raise WeatherIngestionError("Open-Meteo is disabled by configuration.")

    source = _source()
    run = IngestionRun.objects.create(
        source=source,
        status=IngestionRunStatus.RUNNING,
        params={"area": area.slug, "forecast_days": forecast_days, "provider": "open_meteo"},
    )
    try:
        location = _location(area, source)
        payload = open_meteo.fetch_forecast(
            location.latitude,
            location.longitude,
            timezone=location.timezone,
            forecast_days=forecast_days,
            timeout=settings.OPEN_METEO_TIMEOUT,
        )
        normalized = normalize_forecast(payload, timezone=location.timezone)
        retrieved_at = _aware(normalized["meta"]["retrieved_at"])
        records = [*([normalized["current"]] if normalized["current"] else []), *normalized["hourly"], *normalized["daily"]]
        written = _upsert_records(location, source, records, retrieved_at)

        # Keep the rolling forecast window tidy without touching archived history.
        cutoff = timezone.now() - timedelta(hours=48)
        WeatherRecord.objects.filter(
            location=location, source=source, kind=WeatherKind.HOURLY, valid_time__lt=cutoff
        ).delete()
        WeatherRecord.objects.filter(
            location=location,
            source=source,
            kind=WeatherKind.CURRENT,
            retrieved_at__lt=timezone.now() - timedelta(days=2),
        ).delete()

        run.status = IngestionRunStatus.SUCCESS
        run.records_fetched = len(records)
        run.records_written = written
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "records_fetched", "records_written", "finished_at"])
        logger.info("Open-Meteo forecast ingested", extra={"source": source.slug, "status": "SUCCESS"})
        return {
            "fetched": len(records),
            "written": written,
            "current": bool(normalized["current"]),
            "hourly": len(normalized["hourly"]),
            "daily": len(normalized["daily"]),
            "retrieved_at": retrieved_at.isoformat(),
            "run_id": str(run.id),
        }
    except Exception as exc:  # noqa: BLE001 - record every failure then surface it
        run.status = IngestionRunStatus.FAILED
        run.finished_at = timezone.now()
        run.error_message = str(exc)[:2000]
        run.save(update_fields=["status", "finished_at", "error_message"])
        logger.exception("Open-Meteo forecast ingestion failed", extra={"source": source.slug, "status": "FAILED"})
        raise WeatherIngestionError(str(exc)) from exc


def ingest_weather_history(area: Area, *, start: date, end: date) -> dict:
    if not settings.OPEN_METEO_ENABLED:
        raise WeatherIngestionError("Open-Meteo is disabled by configuration.")
    if end < start:
        raise WeatherIngestionError("end date must not precede start date.")

    source = _source()
    run = IngestionRun.objects.create(
        source=source,
        status=IngestionRunStatus.RUNNING,
        params={"area": area.slug, "start": start.isoformat(), "end": end.isoformat(), "dataset": "era5_land_archive"},
    )
    try:
        location = _location(area, source)
        payload = open_meteo.fetch_archive(
            location.latitude,
            location.longitude,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            timezone=location.timezone,
            timeout=max(settings.OPEN_METEO_TIMEOUT, 60),
        )
        normalized = normalize_archive(payload, timezone=location.timezone)
        retrieved_at = _aware(normalized["meta"]["retrieved_at"])
        written = 0
        for day in normalized["days"]:
            valid_time = _aware(day["valid_time"])
            WeatherRecord.objects.update_or_create(
                location=location,
                source=source,
                kind=WeatherKind.DAILY,
                valid_time=valid_time,
                defaults={
                    "retrieved_at": retrieved_at,
                    "quality_status": DataState.AVAILABLE,
                    "temperature_c": day["temperature_mean_c"],
                    "temperature_max_c": day["temperature_max_c"],
                    "temperature_min_c": day["temperature_min_c"],
                    "relative_humidity": day["relative_humidity_mean"],
                    "precipitation_mm": day["precipitation_mm"],
                    "wind_speed_kmh": day["wind_speed_kmh"],
                    "raw": {"date": day["date"], "dataset": "era5_land"},
                },
            )
            written += 1
        run.status = IngestionRunStatus.SUCCESS
        run.records_fetched = len(normalized["days"])
        run.records_written = written
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "records_fetched", "records_written", "finished_at"])
        return {"fetched": len(normalized["days"]), "written": written, "run_id": str(run.id)}
    except Exception as exc:  # noqa: BLE001
        run.status = IngestionRunStatus.FAILED
        run.finished_at = timezone.now()
        run.error_message = str(exc)[:2000]
        run.save(update_fields=["status", "finished_at", "error_message"])
        logger.exception("Open-Meteo archive ingestion failed", extra={"source": source.slug})
        raise WeatherIngestionError(str(exc)) from exc
