"""CPCB air-quality adapter (data.gov.in resource).

Status: interface + normalisation implemented; live access BLOCKED without a
CPCB/data.gov.in API key, and the API host timed out from the development
environment during the initial probe. No station measurement is fabricated.

Docs: https://data.gov.in/  (CPCB real-time AQI resource)
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import requests

IST = ZoneInfo("Asia/Kolkata")
POLLUTANT_MAP = {
    "pm2.5": "pm25",
    "pm25": "pm25",
    "pm10": "pm10",
    "no2": "no2",
    "so2": "so2",
    "co": "co",
    "o3": "o3",
    "ozone": "o3",
}


class CPCBNotConfigured(Exception):
    pass


class CPCBProviderError(Exception):
    pass


@dataclass
class CPCBClient:
    api_key: str
    resource_id: str
    base_url: str = "https://api.data.gov.in/resource"
    timeout: float = 60

    def fetch_page(self, *, limit: int = 1000, offset: int = 0) -> dict:
        if not self.api_key:
            raise CPCBNotConfigured(
                "CPCB_API_KEY is not configured. Station air-quality data remains unavailable; "
                "no measurements are synthesised."
            )
        url = f"{self.base_url.rstrip('/')}/{self.resource_id}"
        try:
            response = requests.get(
                url,
                params={
                    "api-key": self.api_key,
                    "format": "json",
                    "limit": limit,
                    "offset": offset,
                },
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise CPCBProviderError(f"CPCB request failed: {exc}") from exc
        if response.status_code in {401, 403}:
            raise CPCBProviderError(f"CPCB rejected credentials (HTTP {response.status_code}).")
        if response.status_code != 200:
            raise CPCBProviderError(f"CPCB returned HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError as exc:
            raise CPCBProviderError("CPCB returned non-JSON content.") from exc


def station_external_id(city: str, station: str) -> str:
    digest = hashlib.sha1(f"{city.strip().lower()}|{station.strip().lower()}".encode()).hexdigest()
    return digest[:24]


def aqi_category(value: int | None) -> str:
    """CPCB AQI category boundaries (official guidance, not a computed index)."""
    if value is None:
        return ""
    if value <= 50:
        return "Good"
    if value <= 100:
        return "Satisfactory"
    if value <= 200:
        return "Moderate"
    if value <= 300:
        return "Poor"
    if value <= 400:
        return "Very Poor"
    return "Severe"


def normalize_records(payload: dict, *, retrieved_at: datetime | None = None) -> tuple[list[dict], list[str]]:
    """Group CPCB station-pollutant rows into station measurements.

    Rows without coordinates are reported in ``warnings`` and skipped: the
    product does not invent station locations.
    """
    rows = payload.get("records") or payload.get("data") or []
    retrieved = retrieved_at or datetime.now(tz=timezone.utc)
    grouped: dict[tuple[str, str, str], dict] = {}
    warnings: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        station = str(row.get("station") or row.get("station_name") or "").strip()
        city = str(row.get("city") or "").strip()
        if not station:
            continue
        last_update = str(row.get("last_update") or row.get("last_update_time") or "").strip()
        measured_at = _parse_timestamp(last_update)
        if measured_at is None:
            warnings.append(f"Skipped row with invalid timestamp for station {station}.")
            continue
        key = (city, station, measured_at.isoformat())
        entry = grouped.get(key)
        if entry is None:
            latitude = _to_float(row.get("latitude") or row.get("lat"))
            longitude = _to_float(row.get("longitude") or row.get("lon") or row.get("lng"))
            entry = {
                "station": station,
                "city": city,
                "state": str(row.get("state") or "").strip(),
                "latitude": latitude,
                "longitude": longitude,
                "measured_at": measured_at,
                "retrieved_at": retrieved,
                "pollutants": {},
                "aqi": None,
                "raw": {"rows": []},
                "quality_flags": [],
            }
            grouped[key] = entry

        entry["raw"]["rows"].append(row)
        pollutant_id = str(row.get("pollutant_id") or "").strip().lower()
        value = _to_float(row.get("pollutant_avg") or row.get("avg_value") or row.get("value"))
        unit = str(row.get("pollutant_unit") or "").strip()
        if pollutant_id in {"aqi", "air_quality_index"}:
            if value is not None and value >= 0:
                entry["aqi"] = int(round(value))
                entry["raw"]["aqi_unit"] = unit
        elif pollutant_id in POLLUTANT_MAP and value is not None:
            field = POLLUTANT_MAP[pollutant_id]
            if value < 0:
                entry["quality_flags"].append(f"negative_{field}")
            else:
                entry["pollutants"][field] = value
                entry["pollutants"].setdefault("units", {})[field] = unit or "µg/m³"

    results = []
    for entry in grouped.values():
        if entry["latitude"] is None or entry["longitude"] is None:
            warnings.append(f"Station {entry['station']} has no published coordinates; skipped.")
            continue
        if not (-90 <= entry["latitude"] <= 90 and -180 <= entry["longitude"] <= 180):
            warnings.append(f"Station {entry['station']} has out-of-range coordinates; skipped.")
            continue
        if not entry["pollutants"] and entry["aqi"] is None:
            warnings.append(f"Station {entry['station']} had no numeric pollutant readings; skipped.")
            continue
        age = retrieved - entry["measured_at"]
        if age > timedelta(hours=6):
            entry["quality_flags"].append("measurement_older_than_6h")
        entry["external_id"] = station_external_id(entry["city"], entry["station"])
        entry["aqi_category"] = aqi_category(entry["aqi"])
        results.append(entry)
    return results, warnings


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    # CPCB commonly publishes "DD-MM-YYYY HH:MM:SS" or ISO-like timestamps.
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=IST).astimezone(timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=IST)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _to_float(value: Any) -> float | None:
    if value in (None, "", "NA", "N/A", "-"):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def sanitize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
