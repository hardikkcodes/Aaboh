"""Pure normalisation functions for Open-Meteo payloads.

These functions do not import Django. Times are returned as ISO 8601 strings with
explicit offsets; persistence converts them to UTC.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo


def _local_iso(value: str, tz: ZoneInfo) -> str:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tz)
    return parsed.isoformat()


def _day_start_iso(day: str, tz: ZoneInfo) -> str:
    d = date.fromisoformat(day)
    return datetime.combine(d, time(0, 0), tzinfo=tz).isoformat()


def normalize_forecast(payload: dict, *, timezone: str = "Asia/Kolkata") -> dict:
    """Return ``{"current": {...}, "hourly": [...], "daily": [...], "meta": {...}}``."""
    tz = ZoneInfo(timezone)
    retrieved_at = datetime.now(tz=ZoneInfo("UTC")).isoformat()

    current_payload = payload.get("current") or {}
    current = None
    if current_payload.get("time"):
        current = {
            "kind": "CURRENT",
            "valid_time": _local_iso(current_payload["time"], tz),
            "temperature_c": current_payload.get("temperature_2m"),
            "relative_humidity": current_payload.get("relative_humidity_2m"),
            "apparent_temperature_c": current_payload.get("apparent_temperature"),
            "precipitation_mm": current_payload.get("precipitation"),
            "rain_mm": current_payload.get("rain"),
            "showers_mm": current_payload.get("showers"),
            "weather_code": current_payload.get("weather_code"),
            "cloud_cover": current_payload.get("cloud_cover"),
            "pressure_hpa": current_payload.get("pressure_msl"),
            "wind_speed_kmh": current_payload.get("wind_speed_10m"),
            "wind_direction_deg": current_payload.get("wind_direction_10m"),
            "wind_gust_kmh": current_payload.get("wind_gusts_10m"),
            "is_day": bool(current_payload.get("is_day")) if current_payload.get("is_day") is not None else None,
            "raw": current_payload,
        }

    hourly_payload = payload.get("hourly") or {}
    hourly_times = hourly_payload.get("time") or []
    hourly = []
    for index, raw_time in enumerate(hourly_times):
        record = {
            "kind": "HOURLY",
            "valid_time": _local_iso(raw_time, tz),
            "temperature_c": _at(hourly_payload, "temperature_2m", index),
            "relative_humidity": _at(hourly_payload, "relative_humidity_2m", index),
            "apparent_temperature_c": _at(hourly_payload, "apparent_temperature", index),
            "dew_point_c": _at(hourly_payload, "dew_point_2m", index),
            "precipitation_probability": _at(hourly_payload, "precipitation_probability", index),
            "precipitation_mm": _at(hourly_payload, "precipitation", index),
            "rain_mm": _at(hourly_payload, "rain", index),
            "showers_mm": _at(hourly_payload, "showers", index),
            "weather_code": _at(hourly_payload, "weather_code", index),
            "cloud_cover": _at(hourly_payload, "cloud_cover", index),
            "visibility_m": _at(hourly_payload, "visibility", index),
            "wind_speed_kmh": _at(hourly_payload, "wind_speed_10m", index),
            "wind_direction_deg": _at(hourly_payload, "wind_direction_10m", index),
            "wind_gust_kmh": _at(hourly_payload, "wind_gusts_10m", index),
            "shortwave_radiation_wm2": _at(hourly_payload, "shortwave_radiation", index),
            "raw": {"time": raw_time},
        }
        hourly.append(record)

    daily_payload = payload.get("daily") or {}
    daily = []
    for index, raw_day in enumerate(daily_payload.get("time") or []):
        daily.append(
            {
                "kind": "DAILY",
                "valid_time": _day_start_iso(raw_day, tz),
                "weather_code": _at(daily_payload, "weather_code", index),
                "temperature_max_c": _at(daily_payload, "temperature_2m_max", index),
                "temperature_min_c": _at(daily_payload, "temperature_2m_min", index),
                "apparent_temperature_max_c": _at(daily_payload, "apparent_temperature_max", index),
                "apparent_temperature_min_c": _at(daily_payload, "apparent_temperature_min", index),
                "precipitation_mm": _at(daily_payload, "precipitation_sum", index),
                "rain_mm": _at(daily_payload, "rain_sum", index),
                "showers_mm": _at(daily_payload, "showers_sum", index),
                "precipitation_probability": _at(daily_payload, "precipitation_probability_max", index),
                "wind_speed_kmh": _at(daily_payload, "wind_speed_10m_max", index),
                "wind_gust_kmh": _at(daily_payload, "wind_gusts_10m_max", index),
                "wind_direction_deg": _at(daily_payload, "wind_direction_10m_dominant", index),
                "shortwave_radiation_wm2": _at(daily_payload, "shortwave_radiation_sum", index),
                "raw": {"date": raw_day},
            }
        )

    return {
        "current": current,
        "hourly": hourly,
        "daily": daily,
        "meta": {
            "retrieved_at": retrieved_at,
            "timezone": timezone,
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "elevation": payload.get("elevation"),
            "generationtime_ms": payload.get("generationtime_ms"),
            "utc_offset_seconds": payload.get("utc_offset_seconds"),
        },
    }


def normalize_archive(payload: dict, *, timezone: str = "Asia/Kolkata") -> dict:
    """Normalise daily ERA5-Land archive data from Open-Meteo."""
    tz = ZoneInfo(timezone)
    retrieved_at = datetime.now(tz=ZoneInfo("UTC")).isoformat()
    daily_payload = payload.get("daily") or {}
    days = []
    for index, raw_day in enumerate(daily_payload.get("time") or []):
        days.append(
            {
                "date": raw_day,
                "valid_time": _day_start_iso(raw_day, tz),
                "temperature_mean_c": _at(daily_payload, "temperature_2m_mean", index),
                "temperature_max_c": _at(daily_payload, "temperature_2m_max", index),
                "temperature_min_c": _at(daily_payload, "temperature_2m_min", index),
                "precipitation_mm": _at(daily_payload, "precipitation_sum", index),
                "relative_humidity_mean": _at(daily_payload, "relative_humidity_2m_mean", index),
                "wind_speed_kmh": _at(daily_payload, "wind_speed_10m_mean", index),
            }
        )
    return {
        "days": days,
        "meta": {
            "retrieved_at": retrieved_at,
            "timezone": timezone,
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "elevation": payload.get("elevation"),
        },
    }


def _at(payload: dict, key: str, index: int) -> Any:
    values = payload.get(key)
    if not values or index >= len(values):
        return None
    return values[index]


def iter_weather_records(normalized: dict) -> Iterator[dict]:
    if normalized.get("current"):
        yield normalized["current"]
    yield from normalized.get("hourly", [])
    yield from normalized.get("daily", [])


def daily_start(day: str, timezone: str = "Asia/Kolkata") -> datetime:
    return datetime.combine(date.fromisoformat(day), time(0, 0), tzinfo=ZoneInfo(timezone))


def date_range(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]
