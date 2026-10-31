"""Keeps live data current when the separate ingest loop isn't running, as in development."""

from __future__ import annotations

import logging
import threading
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.db import connections
from django.utils import timezone

from apps.core.models import IngestionRun, IngestionRunStatus

logger = logging.getLogger(__name__)
LOCK_KEY = "refresh-data-running"
LOCK_SECONDS = 5 * 60
MAX_AGE = timedelta(minutes=10)


def _refresh() -> None:
    try:
        call_command("refresh_data", verbosity=0)
    except Exception:  # noqa: BLE001 - a background refresh must never reach a visitor
        logger.exception("Background data refresh failed")
    finally:
        connections.close_all()


def refresh_if_old() -> bool:
    if not settings.AUTO_REFRESH_DATA or not cache.add(LOCK_KEY, True, LOCK_SECONDS):
        return False
    latest = IngestionRun.objects.filter(status=IngestionRunStatus.SUCCESS).order_by("-finished_at").first()
    if latest and latest.finished_at and timezone.now() - latest.finished_at < MAX_AGE:
        return False
    threading.Thread(target=_refresh, daemon=True).start()
    return True


class AutoRefreshMiddleware:
    """Checks at most every five minutes, and never slows the request that triggers it."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            refresh_if_old()
        return self.get_response(request)
