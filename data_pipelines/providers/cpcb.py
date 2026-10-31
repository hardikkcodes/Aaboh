"""CPCB air-quality adapter (data.gov.in resource).

The live resource publishes one row per station-pollutant reading. It does not
publish an AQI row and it does not publish a unit field. This adapter therefore:

* preserves every raw row,
* stores pollutant concentrations exactly as published,
* records that the unit was not published, and
* computes a CPCB sub-index AQI only where the documented breakpoints can be
  applied safely. CO is excluded from that computation because its published
  unit cannot be confirmed, and the exclusion is reported.

Docs: https://data.gov.in/  (CPCB real-time AQI resource)
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import requests

IST = ZoneInfo("Asia/Kolkata")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Aaboh/0.1"
POLLUTANT_MAP = {
    "pm2.5": "pm25",
    "pm25": "pm25",
    "pm10": "pm10",
    "no2": "no2",
    "so2": "so2",
    "co": "co",
    "o3": "o3",
    "ozone": "o3",
    "nh3": "nh3",
}

# CPCB national AQI breakpoints. Each entry is (concentration boundaries,
# AQI boundaries). The boundaries are inclusive lower / exclusive upper except
# for the final band, which is clamped to AQI 500.
AQI_BREAKPOINTS: dict[str, tuple[list[float], list[int]]] = {
    "pm25": ([0, 30, 60, 90, 120, 250, 500], [0, 50, 100, 200, 300, 400, 500]),
    "pm10": ([0, 50, 100, 250, 350, 430, 600], [0, 50, 100, 200, 300, 400, 500]),
    "no2": ([0, 40, 80, 180, 280, 400, 600], [0, 50, 100, 200, 300, 400, 500]),
    "so2": ([0, 40, 80, 380, 800, 1600, 2000], [0, 50, 100, 200, 300, 400, 500]),
    "co": ([0, 1, 2, 10, 17, 34, 50], [0, 50, 100, 200, 300, 400, 500]),
    "o3": ([0, 50, 100, 168, 208, 748, 1000], [0, 50, 100, 200, 300, 400, 500]),
    "nh3": ([0, 200, 400, 800, 1200, 1800, 2400], [0, 50, 100, 200, 300, 400, 500]),
}
# Fields expected in micrograms per cubic metre. CO is handled separately.
AQI_MICROGRAM_FIELDS = {"pm25", "pm10", "no2", "so2", "o3", "nh3"}


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
    user_agent: str = USER_AGENT
    max_attempts: int = 3
    retry_backoff_seconds: float = 1.5

    def fetch_page(
        self,
        *,
        limit: int = 1000,
        offset: int = 0,
        city: str | None = None,
        state: str | None = None,
    ) -> dict:
        if not self.api_key:
            raise CPCBNotConfigured(
                "CPCB_API_KEY is not configured. Station air-quality data remains unavailable; "
                "no measurements are synthesised."
            )
        url = f"{self.base_url.rstrip('/')}/{self.resource_id}"
        params: dict[str, Any] = {
            "api-key": self.api_key,
            "format": "json",
            "limit": limit,
            "offset": offset,
        }
        if city:
            params["filters[city]"] = city
        if state:
            params["filters[state]"] = state

        last_error: str = ""
        for attempt in range(1, max(1, self.max_attempts) + 1):
            try:
                response = requests.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                )
            except requests.RequestException as exc:
                # The exception text contains the request URL, which carries the API key.
                last_error = f"CPCB request failed: {type(exc).__name__}."
            else:
                if response.status_code in {401, 403}:
                    raise CPCBProviderError(
                        f"CPCB rejected credentials (HTTP {response.status_code})."
                    )
                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError as exc:
                        raise CPCBProviderError("CPCB returned non-JSON content.") from exc
                last_error = f"CPCB returned HTTP {response.status_code}."
                if response.status_code < 500 and response.status_code != 429:
                    raise CPCBProviderError(last_error)

            if attempt < self.max_attempts:
                time.sleep(self.retry_backoff_seconds * attempt)

        raise CPCBProviderError(last_error or "CPCB request failed after retries.")


def station_external_id(city: str, station: str) -> str:
    digest = hashlib.sha1(f"{city.strip().lower()}|{station.strip().lower()}".encode()).hexdigest()
    return digest[:24]


def aqi_category(value: int | None) -> str:
    """CPCB AQI category boundaries."""
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


def _normalized_unit(value: str | None) -> str:
    text = (value or "").strip().lower().replace("µ", "u").replace("m³", "m3")
    return re.sub(r"\s+", "", text)


def _sub_index(field: str, value: float) -> int | None:
    boundaries, index = AQI_BREAKPOINTS[field]
    if value < boundaries[0]:
        return None
    for position in range(len(index) - 1):
        low, high = boundaries[position], boundaries[position + 1]
        if low <= value < high:
            fraction = (value - low) / (high - low)
            return int(round(index[position] + fraction * (index[position + 1] - index[position])))
    # Concentrations above the last published boundary are clamped to the top
    # of the scale rather than extrapolated.
    return index[-1]


def compute_aqi(pollutants: dict, units: dict[str, str] | None = None) -> tuple[int | None, dict]:
    """Compute a CPCB sub-index AQI, returning the basis for auditability.

    At least three pollutants including PM2.5 or PM10 are required. A value's
    unit must be consistent with the breakpoint table; a blank unit is accepted
    for the microgram fields because that is how the CPCB resource publishes
    them, and the assumption is recorded. CO is only used when the source
    explicitly publishes a milligram unit.
    """
    units = units or {}
    used: dict[str, float] = {}
    excluded: list[str] = []
    assumed_units: list[str] = []
    sub_indices: dict[str, int] = {}

    for field, value in pollutants.items():
        if field == "units" or field not in AQI_BREAKPOINTS:
            continue
        if value is None:
            continue
        unit = _normalized_unit(units.get(field, ""))
        if field == "co":
            if "mg" not in unit:
                excluded.append(field)
                continue
        elif field in AQI_MICROGRAM_FIELDS:
            if not unit:
                assumed_units.append(field)
            elif "ug" not in unit:
                excluded.append(field)
                continue
        sub_index = _sub_index(field, float(value))
        if sub_index is None:
            excluded.append(field)
            continue
        used[field] = float(value)
        sub_indices[field] = sub_index

    has_particulate = "pm25" in used or "pm10" in used
    basis = {
        "method": "cpcb_sub_index",
        "used": sub_indices,
        "excluded": excluded,
        "assumed_units": assumed_units,
        "note": (
            "Computed from CPCB sub-index breakpoints. The source does not publish "
            "an AQI row for every station."
        ),
    }
    if len(used) < 3 or not has_particulate:
        basis["reason"] = (
            "Fewer than three usable pollutants, or neither PM2.5 nor PM10 was "
            "published, so no AQI is computed."
        )
        return None, basis

    basis["aqi"] = max(sub_indices.values())
    return basis["aqi"], basis


def normalize_records(payload: dict, *, retrieved_at: datetime | None = None) -> tuple[list[dict], list[str]]:
    """Group CPCB station-pollutant rows into station measurements.

    Rows without coordinates are reported in ``warnings`` and skipped: the
    product does not invent station locations. Pollutant units are kept exactly
    as published, including "not published".
    """
    rows = payload.get("records") or payload.get("data") or []
    retrieved = retrieved_at or datetime.now(tz=UTC)
    grouped: dict[tuple[str, str, str], dict] = {}
    warnings: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        station = sanitize(str(row.get("station") or row.get("station_name") or ""))
        city = sanitize(str(row.get("city") or ""))
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
                "state": sanitize(str(row.get("state") or "")),
                "latitude": latitude,
                "longitude": longitude,
                "measured_at": measured_at,
                "retrieved_at": retrieved,
                "pollutants": {},
                "pollutant_units": {},
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
                entry["pollutant_units"][field] = unit

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

        if entry["aqi"] is None:
            aqi_value, basis = compute_aqi(entry["pollutants"], entry["pollutant_units"])
            entry["raw"]["aqi_basis"] = basis
            if aqi_value is not None:
                entry["aqi"] = aqi_value
                entry["quality_flags"].append("aqi_computed_from_pollutants")
        else:
            entry["raw"]["aqi_basis"] = {"method": "source_published"}
        if "co" in entry["pollutants"] and not entry["pollutant_units"].get("co"):
            entry["quality_flags"].append("co_unit_not_published")

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
            return datetime.strptime(text, fmt).replace(tzinfo=IST).astimezone(UTC)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=IST)
        return parsed.astimezone(UTC)
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
