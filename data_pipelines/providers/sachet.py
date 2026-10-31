"""SACHET / NDMA official CAP alert adapter.

SACHET is the National Disaster Management Authority's public alert platform.
It publishes the alerts that State Disaster Management Authorities and central
agencies (IMD, CWC, ...) issue, with the same CAP-style fields as a warning
feed. It needs no API key.

The feed is national and each alert carries a free-text ``area_description`` plus
a centroid. It does not publish a polygon, so this adapter never invents one:
scope matching is done on the published area text and the centroid is preserved
in ``raw`` for audit only.

Docs: https://sachet.ndma.gov.in/
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

IST = ZoneInfo("Asia/Kolkata")
DEFAULT_ALERTS_PATH = "/cap_public_website/FetchAllAlertDetails"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Aaboh/0.1"

HAZARD_KEYWORDS = {
    "heavy_rain": ("heavy rain", "heavy rainfall", "very heavy", "extremely heavy", "light rain", "rainfall"),
    "thunderstorm": ("thunder", "lightning", "squall"),
    "heatwave": ("heat wave", "heatwave", "hot day"),
    "cold_wave": ("cold wave", "coldwave", "cold day"),
    "cyclone": ("cyclone", "depression", "storm surge"),
    "fog": ("fog", "visibility"),
    "flood": ("flood", "inundation", "flash flood"),
}

# SACHET publishes a colour band and a separate urgency word ("WATCH"/"ALERT").
# Only the colour maps onto CAP-style severity; the urgency is preserved as-is.
SEVERITY_COLOR_MAP = {
    "red": "extreme",
    "orange": "severe",
    "yellow": "moderate",
    "green": "minor",
}


class SACHETProviderError(Exception):
    pass


@dataclass
class SACHETClient:
    base_url: str = "https://sachet.ndma.gov.in"
    timeout: float = 45
    user_agent: str = USER_AGENT
    max_attempts: int = 3
    retry_backoff_seconds: float = 1.5

    def fetch_all(self) -> list[dict]:
        url = f"{self.base_url.rstrip('/')}{DEFAULT_ALERTS_PATH}"
        last_error = ""
        for attempt in range(1, max(1, self.max_attempts) + 1):
            try:
                response = requests.get(
                    url,
                    timeout=self.timeout,
                    headers={"User-Agent": self.user_agent, "Accept": "application/json"},
                )
            except requests.RequestException as exc:
                last_error = f"SACHET request failed: {exc}"
            else:
                if response.status_code == 200:
                    try:
                        payload = response.json()
                    except ValueError as exc:
                        raise SACHETProviderError("SACHET returned non-JSON content.") from exc
                    if isinstance(payload, list):
                        return payload
                    if isinstance(payload, dict):
                        items = payload.get("data") or payload.get("alerts") or []
                        if isinstance(items, list):
                            return items
                    raise SACHETProviderError("SACHET returned an unexpected payload shape.")
                last_error = f"SACHET returned HTTP {response.status_code}."
                if response.status_code < 500 and response.status_code != 429:
                    raise SACHETProviderError(last_error)

            if attempt < self.max_attempts:
                time.sleep(self.retry_backoff_seconds * attempt)

        raise SACHETProviderError(last_error or "SACHET request failed after retries.")


def classify_hazard(*parts: str) -> str:
    text = " ".join(part for part in parts if part).lower()
    for hazard, keywords in HAZARD_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return hazard
    return "other"


def map_severity(color: Any, urgency: Any) -> str:
    raw_color = str(color or "").strip().lower()
    if raw_color in SEVERITY_COLOR_MAP:
        return SEVERITY_COLOR_MAP[raw_color]
    raw_urgency = str(urgency or "").strip().lower()
    if raw_urgency in SEVERITY_COLOR_MAP:
        return SEVERITY_COLOR_MAP[raw_urgency]
    if raw_urgency in {"alert", "warning"}:
        return "severe"
    if raw_urgency == "watch":
        return "moderate"
    return "unknown"


def parse_alert_time(value: Any) -> datetime | None:
    """Parse the IST text timestamps SACHET publishes.

    Example: ``Sat Oct 31 09:05:00 IST 2026``. ISO strings and naive values are
    also accepted and treated as IST, because that is the feed's timezone.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=IST)
    text = re.sub(r"\s+", " ", str(value).strip())
    for fmt in ("%a %b %d %H:%M:%S IST %Y", "%a %b %d %H:%M:%S %Z %Y", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=IST)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=IST)


def parse_centroid(value: Any) -> tuple[float, float] | None:
    """Return ``(latitude, longitude)`` from the feed's ``\"lon,lat\"`` string."""
    if not value:
        return None
    parts = [part.strip() for part in str(value).split(",")]
    if len(parts) != 2:
        return None
    try:
        longitude, latitude = float(parts[0]), float(parts[1])
    except ValueError:
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return latitude, longitude


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_alerts(payload: Any, *, retrieved_at: datetime | None = None) -> list[dict]:
    """Normalise SACHET alerts without inventing missing CAP fields.

    ``issued_at`` is set to the published effective start because the feed does
    not publish a separate issue time; the raw record keeps that distinction
    visible through ``quality_notes``. Geometry stays empty because only a
    centroid is published.
    """
    items = payload if isinstance(payload, list) else []
    retrieved = retrieved_at or datetime.now(tz=UTC)
    normalized: list[dict] = []

    for item in items:
        if not isinstance(item, dict):
            continue
        identifier = item.get("identifier") or item.get("alert_id_sdma_autoinc")
        external_id = _clean(identifier) or hashlib.sha256(
            json.dumps(item, sort_keys=True, default=str).encode()
        ).hexdigest()[:32]
        disaster_type = _clean(item.get("disaster_type")) or "Official alert"
        alert_source = _clean(item.get("alert_source"))
        title = f"{disaster_type} - {alert_source}" if alert_source else disaster_type
        description = _clean(item.get("warning_message"))
        areas_text = _clean(item.get("area_description"))
        effective_at = parse_alert_time(item.get("effective_start_time"))
        expires_at = parse_alert_time(item.get("effective_end_time"))
        centroid = parse_centroid(item.get("centroid"))
        issued_at = effective_at or retrieved

        quality_notes = [
            "SACHET does not publish a separate issue time; issued_at uses the effective start time.",
            "SACHET publishes a centroid but no polygon; scope matching uses the published area text.",
        ]
        if item.get("actual_lang") and item.get("actual_lang") != "en":
            quality_notes.append(
                f"Warning text is published in '{item.get('actual_lang')}' and may not render cleanly."
            )

        normalized.append(
            {
                "external_id": external_id[:200],
                "title": title[:300],
                "description": description,
                "hazard": classify_hazard(disaster_type, description),
                "severity": map_severity(item.get("severity_color"), item.get("severity")),
                "certainty": _clean(item.get("severity_level")),
                "urgency": _clean(item.get("severity")),
                "issued_at": issued_at,
                "effective_at": effective_at,
                "expires_at": expires_at,
                "areas_text": areas_text,
                "geometry": None,
                "source_url": "https://sachet.ndma.gov.in/",
                "raw": {
                    "record": item,
                    "centroid": {"latitude": centroid[0], "longitude": centroid[1]}
                    if centroid
                    else None,
                    "area_covered_km2": item.get("area_covered"),
                    "quality_notes": quality_notes,
                },
                "quality_status": "PARTIAL",
                "retrieved_at": retrieved,
            }
        )
    return normalized


def scope_matches(areas_text: str, terms: list[str]) -> bool:
    """Case-insensitive match of published area text against configured terms."""
    text = (areas_text or "").lower()
    return any(term.lower() in text for term in terms if term)
