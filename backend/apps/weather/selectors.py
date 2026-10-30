from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone

from .models import WeatherKind, WeatherRecord

IST = ZoneInfo("Asia/Kolkata")


def source_slug() -> str:
    return "open_meteo"


def current_record(area_slug: str):
    return (
        WeatherRecord.objects.filter(
            location__area__slug=area_slug, source__slug=source_slug(), kind=WeatherKind.CURRENT
        )
        .select_related("source", "location")
        .order_by("-retrieved_at")
        .first()
    )


def hourly_records(area_slug: str, *, hours: int = 48):
    now = timezone.now()
    return (
        WeatherRecord.objects.filter(
            location__area__slug=area_slug,
            source__slug=source_slug(),
            kind=WeatherKind.HOURLY,
            valid_time__gte=now - timedelta(hours=1),
            valid_time__lte=now + timedelta(hours=hours),
        )
        .select_related("source", "location")
        .order_by("valid_time")
    )


def daily_records(area_slug: str, *, days: int = 7):
    today_local = timezone.now().astimezone(IST).date()
    start = datetime.combine(today_local, time(0, 0), tzinfo=IST)
    return (
        WeatherRecord.objects.filter(
            location__area__slug=area_slug,
            source__slug=source_slug(),
            kind=WeatherKind.DAILY,
            valid_time__gte=start,
            valid_time__lt=start + timedelta(days=days + 1),
        )
        .select_related("source")
        .order_by("valid_time")
    )


def history_records(area_slug: str, *, start: date, end: date):
    start_dt = datetime.combine(start, time(0, 0), tzinfo=IST)
    end_dt = datetime.combine(end + timedelta(days=1), time(0, 0), tzinfo=IST)
    return (
        WeatherRecord.objects.filter(
            location__area__slug=area_slug,
            source__slug=source_slug(),
            kind=WeatherKind.DAILY,
            valid_time__gte=start_dt,
            valid_time__lt=end_dt,
        )
        .select_related("source")
        .order_by("valid_time")
    )


def latest_retrieved_at(records) -> datetime | None:
    latest = None
    for record in records:
        if latest is None or record.retrieved_at > latest:
            latest = record.retrieved_at
    return latest
