"""Geometry helpers built on Shapely and pyproj.

The development runtime stores GeoJSON in a portable JSON column. These helpers
provide the spatial operations the product needs (validation, area, centroid,
distance, bounding boxes) without requiring a native GEOS/GDAL installation.
See ``docs/DECISIONS.md`` ADR-003 for the PostGIS migration path.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from typing import Any

from pyproj import Geod, Transformer
from shapely.geometry import Point, mapping, shape
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

WGS84 = "EPSG:4326"
UTM_KOLKATA = "EPSG:32645"
GEOD = Geod(ellps="WGS84")

_to_utm = Transformer.from_crs(WGS84, UTM_KOLKATA, always_xy=True)
_to_wgs84 = Transformer.from_crs(UTM_KOLKATA, WGS84, always_xy=True)


def parse_geometry(value: Any) -> BaseGeometry:
    """Return a Shapely geometry for a GeoJSON mapping or geometry object."""
    if isinstance(value, BaseGeometry):
        return value
    if not isinstance(value, dict):
        raise ValueError("Geometry must be a GeoJSON object.")
    if value.get("type") == "Feature":
        value = value.get("geometry")
    if not isinstance(value, dict) or "type" not in value:
        raise ValueError("Geometry must include a GeoJSON type.")
    try:
        geom = shape(value)
    except Exception as exc:  # noqa: BLE001 - convert library errors to a stable API error
        raise ValueError("Invalid GeoJSON geometry.") from exc
    if geom.is_empty:
        raise ValueError("Geometry must not be empty.")
    if not geom.is_valid:
        geom = make_valid(geom)
        if geom.is_empty:
            raise ValueError("Geometry is invalid and could not be repaired.")
    return geom


def geometry_to_json(geom: BaseGeometry) -> dict:
    """Serialise a Shapely geometry to JSON-safe GeoJSON."""
    return json.loads(json.dumps(mapping(geom)))


def validate_geometry(value: Any, allowed_types: Iterable[str] | None = None) -> dict:
    geom = parse_geometry(value)
    if allowed_types and geom.geom_type not in set(allowed_types):
        allowed = ", ".join(sorted(allowed_types))
        raise ValueError(f"Unsupported geometry type {geom.geom_type}; expected one of {allowed}.")
    return geometry_to_json(geom)


def centroid_point(value: Any) -> Point:
    geom = parse_geometry(value)
    point = geom.centroid
    if not geom.covers(point):
        # Fall back to a point guaranteed inside the polygon (representative_point).
        point = geom.representative_point()
    return point


def geodesic_area_km2(value: Any) -> float:
    geom = parse_geometry(value)
    area_m2, _ = GEOD.geometry_area_perimeter(geom)
    return round(abs(area_m2) / 1_000_000, 6)


def geometry_bounds(value: Any) -> tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat)."""
    return tuple(parse_geometry(value).bounds)  # type: ignore[return-value]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_008.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def bbox_around_point(lat: float, lon: float, radius_m: float) -> tuple[float, float, float, float]:
    """Bounding box (min_lat, min_lon, max_lat, max_lon) for a radius search."""
    lat_delta = radius_m / 111_320
    cos_lat = max(math.cos(math.radians(lat)), 0.01)
    lon_delta = radius_m / (111_320 * cos_lat)
    return lat - lat_delta, lon - lon_delta, lat + lat_delta, lon + lon_delta


def point_in_geometry(lat: float, lon: float, value: Any) -> bool:
    return parse_geometry(value).covers(Point(lon, lat))


def project_to_utm(value: Any) -> BaseGeometry:
    from shapely.ops import transform

    return transform(_to_utm.transform, parse_geometry(value))


def project_to_wgs84(geom: BaseGeometry) -> BaseGeometry:
    from shapely.ops import transform

    return transform(_to_wgs84.transform, geom)


def utm_bounds(value: Any) -> tuple[float, float, float, float]:
    return project_to_utm(value).bounds


def point_geojson(lat: float, lon: float) -> dict:
    return {"type": "Point", "coordinates": [lon, lat]}


def bbox_geojson(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> dict:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat],
            ]
        ],
    }
