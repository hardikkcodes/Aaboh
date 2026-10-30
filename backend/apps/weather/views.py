from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.quality import DataState, freshness_state
from apps.core.serializers import source_summary
from apps.locations.models import Area

from .selectors import (
    current_record,
    daily_records,
    history_records,
    hourly_records,
    latest_retrieved_at,
)
from .serializers import WeatherRecordSerializer, WeatherLocationSerializer


def _area(request) -> Area:
    slug = request.query_params.get("area", "kolkata")
    try:
        return Area.objects.get(slug=slug, is_active=True)
    except Area.DoesNotExist as exc:
        raise ValidationError({"area": f"Unknown area: {slug}"}) from exc


def _source_of(records, area: Area):
    if records:
        return records[0].source
    location = area.weather_locations.select_related("source").first()
    return location.source if location else None


class WeatherCurrentView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        area = _area(request)
        record = current_record(area.slug)
        state = DataState.UNAVAILABLE
        if record:
            state = freshness_state(record.retrieved_at, max_age=timedelta(hours=3))
        source = _source_of([record] if record else [], area)
        return Response(
            {
                "area": {"slug": area.slug, "name": area.name},
                "state": state,
                "source": source_summary(source, dataset="Open-Meteo forecast"),
                "observed_at": record.valid_time if record else None,
                "retrieved_at": record.retrieved_at if record else None,
                "record": WeatherRecordSerializer(record).data if record else None,
                "note": (
                    "Current conditions are a provider forecast/analysis point, not an official station observation."
                    if record
                    else "No current weather data has been ingested yet."
                ),
            }
        )


class WeatherForecastView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        area = _area(request)
        try:
            hours = min(max(int(request.query_params.get("hours", 48)), 1), 96)
        except ValueError as exc:
            raise ValidationError({"hours": "Must be an integer."}) from exc
        current = current_record(area.slug)
        hourly = list(hourly_records(area.slug, hours=hours))
        daily = list(daily_records(area.slug, days=7))
        retrieved = latest_retrieved_at([*([current] if current else []), *hourly, *daily])
        source = _source_of([current] if current else hourly, area)
        state = freshness_state(retrieved, max_age=timedelta(hours=3)) if retrieved else DataState.UNAVAILABLE
        return Response(
            {
                "area": {"slug": area.slug, "name": area.name},
                "state": state,
                "source": source_summary(source, dataset="Open-Meteo forecast"),
                "generated_at": timezone.now(),
                "retrieved_at": retrieved,
                "current": WeatherRecordSerializer(current).data if current else None,
                "hourly": WeatherRecordSerializer(hourly, many=True).data,
                "daily": WeatherRecordSerializer(daily, many=True).data,
                "note": "Forecast values are not official warnings. Official warnings are shown separately.",
            }
        )


class WeatherHistoryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        area = _area(request)
        today = timezone.now().date()
        try:
            end = date.fromisoformat(request.query_params["end_date"]) if request.query_params.get("end_date") else today
            start = (
                date.fromisoformat(request.query_params["start_date"])
                if request.query_params.get("start_date")
                else end - timedelta(days=90)
            )
        except ValueError as exc:
            raise ValidationError({"date": "Dates must use YYYY-MM-DD."}) from exc
        if end < start:
            raise ValidationError({"end_date": "Must not precede start_date."})
        if (end - start).days > 730:
            raise ValidationError({"start_date": "Maximum history window is 730 days."})

        records = list(history_records(area.slug, start=start, end=min(end, today)))
        retrieved = latest_retrieved_at(records)
        source = _source_of(records, area)
        return Response(
            {
                "area": {"slug": area.slug, "name": area.name},
                "state": DataState.AVAILABLE if records else DataState.UNAVAILABLE,
                "source": source_summary(source, dataset="ERA5-Land daily archive (via Open-Meteo)"),
                "start_date": start,
                "end_date": end,
                "retrieved_at": retrieved,
                "daily": WeatherRecordSerializer(records, many=True).data,
                "note": (
                    "Daily historical values are aggregated reanalysis data (ERA5-Land, ~9 km), "
                    "not neighbourhood station observations."
                ),
            }
        )


class WeatherLocationsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        area = _area(request)
        locations = area.weather_locations.select_related("source")
        return Response({"area": area.slug, "results": WeatherLocationSerializer(locations, many=True).data})
