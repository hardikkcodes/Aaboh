from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class NotificationKind(models.TextChoices):
    OFFICIAL_ALERT = "official_alert", "Official alert"
    ROUTE_REPORT = "route_report", "Report on your route"
    PLACE_REPORT = "place_report", "Report near your place"
    HEAVY_RAIN = "heavy_rain", "Heavy rain soon"
    HEAT = "heat", "Heat"
    ROUTE_RAIN = "route_rain", "Rain near your leaving time"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=24, choices=NotificationKind.choices)
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=500, blank=True)
    link = models.CharField(max_length=200, blank=True)
    dedupe_key = models.CharField(max_length=120)
    read_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "dedupe_key"], name="uniq_notification_per_event")
        ]
        indexes = [models.Index(fields=["user", "-created_at"], name="notification_user_idx")]

    def __str__(self) -> str:
        return self.title
