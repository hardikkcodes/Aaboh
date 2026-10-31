"""Active cyclones from GDACS. Only a recent successful read is ever shown."""

from __future__ import annotations

from datetime import timedelta

from data_pipelines.providers.gdacs import fetch_active_cyclones
from django.utils import timezone

from apps.core.geometry import haversine_m

from .models import TropicalCyclone

KOLKATA = (22.57, 88.36)
MAX_AGE = timedelta(hours=6)


def ingest_cyclones() -> int:
    storms = fetch_active_cyclones()
    for storm in storms:
        TropicalCyclone.objects.update_or_create(
            event_id=storm["event_id"],
            defaults={
                **{key: value for key, value in storm.items() if key != "event_id"},
                "distance_km": round(haversine_m(*KOLKATA, storm["latitude"], storm["longitude"]) / 1000),
            },
        )
    TropicalCyclone.objects.exclude(event_id__in=[storm["event_id"] for storm in storms]).delete()
    return len(storms)


def active_cyclones(*, now=None) -> list[TropicalCyclone]:
    now = now or timezone.now()
    return list(TropicalCyclone.objects.filter(retrieved_at__gte=now - MAX_AGE).order_by("distance_km"))
