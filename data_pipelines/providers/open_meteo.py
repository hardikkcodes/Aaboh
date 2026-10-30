"""Open-Meteo provider adapter.

Open-Meteo is a supplementary, non-official source (CC BY 4.0). It is used for
current conditions, forecasts and archive access to ERA5-Land. Official Indian
warnings are never derived from this provider.

Docs: https://open-meteo.com/en/docs
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
DEFAULT_TIMEZONE = "Asia/Kolkata"

CURRENT_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "is_day",
    "precipitation",
    "rain",
    "showers",
    "weather_code",
    "cloud_cover",
    "pressure_msl",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
]
HOURLY_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "dew_point_2m",
    "precipitation_probability",
    "precipitation",
    "rain",
    "showers",
    "weather_code",
    "cloud_cover",
    "visibility",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
]
DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "precipitation_sum",
    "rain_sum",
    "showers_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "wind_direction_10m_dominant",
    "shortwave_radiation_sum",
]
ARCHIVE_DAILY_FIELDS = [
    "temperature_2m_mean",
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "relative_humidity_2m_mean",
    "wind_speed_10m_mean",
]


@dataclass
class ProviderError(Exception):
    message: str
    status_code: int | None = None

    def __str__(self) -> str:
        return self.message


def _request(url: str, params: dict[str, Any], timeout: float) -> dict:
    try:
        response = requests.get(
            url,
            params=params,
            timeout=timeout,
            headers={"User-Agent": "CivicClimateIntelligence/0.1 (environmental research; contact: local dev)"},
        )
    except requests.RequestException as exc:
        raise ProviderError(f"Open-Meteo request failed: {exc}") from exc
    if response.status_code != 200:
        raise ProviderError(
            f"Open-Meteo returned HTTP {response.status_code}: {response.text[:300]}",
            status_code=response.status_code,
        )
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError("Open-Meteo returned non-JSON content.") from exc


def fetch_forecast(
    latitude: float,
    longitude: float,
    *,
    timezone: str = DEFAULT_TIMEZONE,
    forecast_days: int = 7,
    timeout: float = 30,
) -> dict:
    params = {
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "current": ",".join(CURRENT_FIELDS),
        "hourly": ",".join(HOURLY_FIELDS),
        "daily": ",".join(DAILY_FIELDS),
        "timezone": timezone,
        "forecast_days": max(1, min(forecast_days, 16)),
        "wind_speed_unit": "kmh",
        "timeformat": "iso8601",
    }
    return _request(FORECAST_URL, params, timeout)


def fetch_archive(
    latitude: float,
    longitude: float,
    *,
    start_date: str,
    end_date: str,
    timezone: str = DEFAULT_TIMEZONE,
    timeout: float = 60,
) -> dict:
    params = {
        "latitude": round(latitude, 4),
        "longitude": round(longitude, 4),
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(ARCHIVE_DAILY_FIELDS),
        "timezone": timezone,
        "wind_speed_unit": "kmh",
        "timeformat": "iso8601",
    }
    return _request(ARCHIVE_URL, params, timeout)
