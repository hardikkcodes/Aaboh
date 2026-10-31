"""IMD official warning adapter.

Status: integration interface implemented, live access BLOCKED on an API key.

The public IMD API returns ``{"error":"API key missing"}`` without credentials.
The exact authentication header is not stated on the public reference page; the
header name is therefore configurable (``IMD_API_KEY_HEADER``, default
``X-API-Key``) and must be confirmed when credentials are issued. No official
alert is fabricated when the provider is unavailable.

Docs: https://api.imd.gov.in/public/api_reference.html
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import requests


class IMDNotConfigured(Exception):
    pass


class IMDProviderError(Exception):
    pass


@dataclass
class IMDClient:
    api_key: str
    base_url: str = "https://api.imd.gov.in/api/v1"
    api_key_header: str = "X-API-Key"
    timeout: float = 45

    def _get(self, path: str, params: dict | None = None) -> dict:
        if not self.api_key:
            raise IMDNotConfigured(
                "IMD_API_KEY is not configured. Official warnings remain unavailable; no substitute is fabricated."
            )
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        try:
            response = requests.get(
                url,
                params=params or {},
                headers={self.api_key_header: self.api_key, "Accept": "application/json"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise IMDProviderError(f"IMD request failed: {exc}") from exc
        if response.status_code in {401, 403}:
            raise IMDProviderError(f"IMD rejected credentials (HTTP {response.status_code}).")
        if response.status_code != 200:
            raise IMDProviderError(f"IMD returned HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError as exc:
            raise IMDProviderError("IMD returned non-JSON content.") from exc

    def district_warnings(self, district_id: str | None = None) -> dict:
        params = {"id": district_id} if district_id else None
        return self._get("districtwarning", params)


HAZARD_KEYWORDS = {
    "heavy_rain": ("heavy rain", "heavy rainfall", "very heavy", "extremely heavy"),
    "thunderstorm": ("thunder", "lightning", "squall"),
    "heatwave": ("heat wave", "heatwave", "hot day"),
    "cold_wave": ("cold wave", "coldwave", "cold day"),
    "cyclone": ("cyclone", "depression", "storm surge"),
    "fog": ("fog", "visibility"),
    "flood": ("flood", "inundation"),
}

SEVERITY_MAP = {
    "red": "extreme",
    "orange": "severe",
    "yellow": "moderate",
    "green": "minor",
    "no warning": "minor",
}


def classify_hazard(text: str) -> str:
    lowered = text.lower()
    for hazard, keywords in HAZARD_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return hazard
    return "other"


def map_severity(value: Any, text: str) -> str:
    raw = str(value or "").strip().lower()
    if raw in SEVERITY_MAP:
        return SEVERITY_MAP[raw]
    for token, severity in SEVERITY_MAP.items():
        if token in text.lower():
            return severity
    return "unknown"


def _first(item: dict, *keys: str) -> Any:
    for key in keys:
        if key in item and item[key] not in (None, ""):
            return item[key]
    return None


def normalize_warnings(payload: Any, *, retrieved_at: datetime | None = None) -> list[dict]:
    """Best-effort normalisation that preserves the raw record.

    The live IMD district-warning schema could not be verified without a key. The
    normaliser accepts a list or a dict containing ``data``/``warnings``. Any
    field it cannot map is preserved in ``raw`` and the alert remains marked with
    quality status PARTIAL rather than being presented as complete.
    """
    items: list[Any]
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("data") or payload.get("warnings") or payload.get("warning") or []
        if isinstance(items, dict):
            items = [items]
    else:
        items = []

    retrieved = retrieved_at or datetime.now(tz=UTC)
    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(_first(item, "title", "warning", "headline", "type", "warning_type") or "IMD district warning")
        description = str(_first(item, "description", "message", "text", "warning_message") or "")
        combined = f"{title} {description}"
        external_id = str(
            _first(item, "id", "warning_id", "alert_id")
            or hashlib.sha256(json.dumps(item, sort_keys=True, default=str).encode()).hexdigest()[:32]
        )
        issued_raw = _first(item, "issued_at", "issue_time", "date", "issued")
        issued_at = _parse_dt(issued_raw) or retrieved
        expires_at = _parse_dt(_first(item, "expires_at", "valid_until", "valid_till", "end_time"))
        normalized.append(
            {
                "external_id": external_id,
                "title": title[:300],
                "description": description,
                "hazard": classify_hazard(combined),
                "severity": map_severity(_first(item, "severity", "color", "alert_level"), combined),
                "certainty": str(_first(item, "certainty") or ""),
                "urgency": str(_first(item, "urgency") or ""),
                "issued_at": issued_at,
                "effective_at": _parse_dt(_first(item, "effective_at", "valid_from", "start_time")),
                "expires_at": expires_at,
                "areas_text": str(_first(item, "areas", "district", "area", "region") or ""),
                "source_url": "https://mausam.imd.gov.in/",
                "raw": item,
                "quality_status": "PARTIAL",
            }
        )
    return normalized


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None
