"""Google place search and routing. The key stays on the server and never reaches a browser."""

from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"
PLACE_URL = "https://places.googleapis.com/v1/places/"
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
TIMEOUT_SECONDS = 8
SEARCH_CENTRE = {"latitude": 22.57, "longitude": 88.36}
SEARCH_RADIUS_M = 50000
MAX_ROUTE_POINTS = 100


class MapsUnavailable(Exception):
    pass


def enabled() -> bool:
    return bool(settings.GOOGLE_MAPS_API_KEY)


def _call(method: str, url: str, *, mask: str | None = None, **kwargs) -> dict:
    headers = {"X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY}
    if mask:
        headers["X-Goog-FieldMask"] = mask
    try:
        response = requests.request(method, url, headers=headers, timeout=TIMEOUT_SECONDS, **kwargs)
    except requests.RequestException as exc:
        logger.warning("Google Maps request failed: %s", type(exc).__name__)
        raise MapsUnavailable from exc
    if response.status_code != 200:
        logger.warning("Google Maps returned HTTP %s", response.status_code)
        raise MapsUnavailable
    return response.json()


def autocomplete(text: str, session: str) -> list[dict]:
    payload = _call(
        "POST",
        AUTOCOMPLETE_URL,
        json={
            "input": text,
            "sessionToken": session,
            "includedRegionCodes": ["in"],
            "locationBias": {"circle": {"center": SEARCH_CENTRE, "radius": SEARCH_RADIUS_M}},
        },
    )
    results = []
    for item in payload.get("suggestions") or []:
        place = item.get("placePrediction")
        if place:
            structured = place.get("structuredFormat") or {}
            results.append(
                {
                    "place_id": place["placeId"],
                    "title": (structured.get("mainText") or {}).get("text") or place["text"]["text"],
                    "subtitle": (structured.get("secondaryText") or {}).get("text") or "",
                }
            )
    return results


def place_details(place_id: str, session: str) -> dict:
    payload = _call(
        "GET",
        PLACE_URL + requests.utils.quote(place_id, safe=""),
        mask="displayName,formattedAddress,location",
        params={"sessionToken": session},
    )
    location = payload.get("location")
    if not location:
        raise MapsUnavailable
    return {
        "title": (payload.get("displayName") or {}).get("text") or "",
        "subtitle": payload.get("formattedAddress") or "",
        "latitude": location["latitude"],
        "longitude": location["longitude"],
    }


def decode_polyline(encoded: str) -> list[list[float]]:
    """Google's encoded polyline format, as [latitude, longitude] pairs."""
    points, index, latitude, longitude = [], 0, 0, 0
    while index < len(encoded):
        deltas = []
        for _ in range(2):
            shift, result = 0, 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        latitude += deltas[0]
        longitude += deltas[1]
        points.append([latitude / 1e5, longitude / 1e5])
    return points


def thin(points: list[list[float]]) -> list[list[float]]:
    if len(points) <= MAX_ROUTE_POINTS:
        return points
    step = (len(points) - 1) / (MAX_ROUTE_POINTS - 1)
    return [points[round(position * step)] for position in range(MAX_ROUTE_POINTS)]


def plan_route(origin: list[float], destination: list[float]) -> dict:
    def waypoint(point):
        return {"location": {"latLng": {"latitude": point[0], "longitude": point[1]}}}

    payload = _call(
        "POST",
        ROUTES_URL,
        mask="routes.polyline.encodedPolyline,routes.distanceMeters,routes.duration",
        json={"origin": waypoint(origin), "destination": waypoint(destination), "travelMode": "DRIVE"},
    )
    routes = payload.get("routes") or []
    if not routes:
        raise MapsUnavailable
    route = routes[0]
    return {
        "points": thin(decode_polyline(route["polyline"]["encodedPolyline"])),
        "distance_m": route.get("distanceMeters"),
    }
