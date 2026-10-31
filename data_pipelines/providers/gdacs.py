"""GDACS tropical cyclone feed, a free UN and European Commission service.

It needs no key. Aaboh shows what GDACS publishes and never makes its own track or
forecast. In India, official cyclone warnings come from IMD.

Docs: https://www.gdacs.org/
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import requests

EVENTS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"
TIMEOUT_SECONDS = 30
LOOKBACK_DAYS = 14
# The Bay of Bengal and Arabian Sea, the basin that can reach West Bengal.
MIN_LATITUDE, MAX_LATITUDE = 0, 30
MIN_LONGITUDE, MAX_LONGITUDE = 50, 105


def parse_events(payload: dict[str, Any]) -> list[dict]:
    storms = []
    for feature in payload.get("features") or []:
        properties = feature.get("properties") or {}
        coordinates = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coordinates) < 2 or str(properties.get("iscurrent", "")).lower() != "true":
            continue
        longitude, latitude = float(coordinates[0]), float(coordinates[1])
        if not (MIN_LATITUDE <= latitude <= MAX_LATITUDE and MIN_LONGITUDE <= longitude <= MAX_LONGITUDE):
            continue
        storms.append(
            {
                "event_id": str(properties["eventid"]),
                "name": properties.get("eventname") or properties.get("name") or "Tropical cyclone",
                "alert_level": properties.get("alertlevel") or "",
                "latitude": latitude,
                "longitude": longitude,
                "report_url": (properties.get("url") or {}).get("report") or "",
            }
        )
    return storms


def fetch_active_cyclones(*, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(UTC)
    response = requests.get(
        EVENTS_URL,
        params={
            "eventlist": "TC",
            "alertlevel": "Green;Orange;Red",
            "fromdate": (now - timedelta(days=LOOKBACK_DAYS)).date().isoformat(),
            "todate": now.date().isoformat(),
        },
        timeout=TIMEOUT_SECONDS,
    )
    # The feed answers 204 with no body when nothing is active.
    if response.status_code == 204 or not response.content:
        return []
    response.raise_for_status()
    return parse_events(response.json())
