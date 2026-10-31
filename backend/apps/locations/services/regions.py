from __future__ import annotations

from ..models import Area, AreaLevel


def reporting_areas():
    """Areas that own reports. Zones overlap their parent city, so they are left out."""
    return Area.objects.filter(is_active=True).exclude(level=AreaLevel.ZONE).order_by("area_km2")


def area_for_point(latitude: float, longitude: float) -> Area | None:
    """The smallest covered area containing a point, so Kolkata wins over a district."""
    return next((area for area in reporting_areas() if area.covers(latitude, longitude)), None)
