from __future__ import annotations

from django.db import models


class RainOutlook(models.Model):
    """The latest rain chances for an area, counted from ensemble forecast runs."""

    area = models.OneToOneField("locations.Area", on_delete=models.CASCADE, related_name="rain_outlook")
    payload = models.JSONField()
    retrieved_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Rain outlook for {self.area_id}"
