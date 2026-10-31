"""How a neighbourhood compares with the rest of its city, from stored real data."""

from __future__ import annotations

from collections import defaultdict
from statistics import median

from django.core.cache import cache

from apps.environment.models import EnvironmentalObservation
from apps.environment.terrain import nearest_terrain
from apps.locations.models import Area

CACHE_SECONDS = 6 * 60 * 60
MIN_CELLS = 10


def _cell_medians(area: Area) -> dict:
    """Each cell's typical ground heat and greenery over every stored satellite date."""
    key = f"cell-medians:{area.pk}"
    stored = cache.get(key)
    if stored is not None:
        return stored
    heat, green = defaultdict(list), defaultdict(list)
    rows = EnvironmentalObservation.objects.filter(cell__area=area).values_list("cell_id", "lst_c", "ndvi")
    for cell, lst, ndvi in rows.iterator():
        if lst is not None:
            heat[cell].append(lst)
        if ndvi is not None:
            green[cell].append(ndvi)
    medians = {
        "heat": {cell: median(values) for cell, values in heat.items()},
        "green": {cell: median(values) for cell, values in green.items()},
    }
    cache.set(key, medians, CACHE_SECONDS)
    return medians


def _share_below(values: dict, cell) -> int | None:
    """The percentage of the city's cells below this one."""
    if cell not in values or len(values) < MIN_CELLS:
        return None
    own = values[cell]
    return round(100 * sum(value < own for value in values.values()) / len(values))


def place_scorecard(area: Area, latitude: float, longitude: float) -> dict | None:
    terrain = nearest_terrain(area, latitude, longitude)
    if terrain is None:
        return None
    medians = _cell_medians(area.data_area)
    cell = terrain.cell_id
    return {
        "hotter_than_pct": _share_below(medians["heat"], cell),
        "greener_than_pct": _share_below(medians["green"], cell),
        "ground_class": terrain.terrain_class,
        "relative_elevation_m": terrain.relative_elevation_m,
        "note": "Compared with the rest of the city, using every stored satellite date. Each figure covers about 1 km.",
    }
