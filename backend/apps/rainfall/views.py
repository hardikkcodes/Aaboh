from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.quality import DataState
from apps.core.serializers import source_summary
from apps.locations.models import Area
from apps.weather.selectors import daily_records, history_records, hourly_records
from apps.weather.serializers import WeatherRecordSerializer

IST = ZoneInfo("Asia/Kolkata")


def _area(request) -> Area:
    slug = request.query_params.get("area", "kolkata")
    try:
        return Area.objects.get(slug=slug, is_active=True)
    except Area.DoesNotExist as exc:
        raise ValidationError({"area": f"Unknown area: {slug}"}) from exc


def _source(records):
    return records[0].source if records else None


class RainfallForecastView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        area = _area(request)
        hourly = list(hourly_records(area.slug, hours=24))
        daily = list(daily_records(area.slug, days=3))
        source = _source(hourly or daily)
        total_24h = round(sum((r.precipitation_mm or 0) for r in hourly), 2)
        peak_hour = max(hourly, key=lambda r: r.precipitation_mm or 0, default=None)
        max_probability = max((r.precipitation_probability or 0) for r in hourly) if hourly else None
        return Response(
            {
                "area": {"slug": area.slug, "name": area.name},
                "state": DataState.AVAILABLE if hourly or daily else DataState.UNAVAILABLE,
                "source": source_summary(source, dataset="Open-Meteo forecast"),
                "generated_at": timezone.now(),
                "retrieved_at": (hourly[0].retrieved_at if hourly else daily[0].retrieved_at if daily else None),
                "summary": {
                    "next_24h_total_mm": total_24h,
                    "next_24h_max_probability_pct": max_probability,
                    "peak_hour": peak_hour.valid_time if peak_hour else None,
                    "peak_hour_mm": peak_hour.precipitation_mm if peak_hour else None,
                },
                "hourly": WeatherRecordSerializer(hourly, many=True).data,
                "daily": WeatherRecordSerializer(daily, many=True).data,
                "note": (
                    "Forecast rainfall is not a flood or waterlogging prediction. Community reports "
                    "and official warnings are separate data layers."
                ),
            }
        )


class RainfallHistoryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        area = _area(request)
        try:
            days = min(max(int(request.query_params.get("days", 90)), 7), 730)
        except ValueError as exc:
            raise ValidationError({"days": "Must be an integer."}) from exc
        end = timezone.now().astimezone(IST).date()
        start = end - timedelta(days=days)
        records = list(history_records(area.slug, start=start, end=end))
        source = _source(records)

        monthly: dict[str, float] = defaultdict(float)
        monthly_days: dict[str, int] = defaultdict(int)
        for record in records:
            key = record.valid_time.astimezone(IST).strftime("%Y-%m")
            monthly[key] += record.precipitation_mm or 0
            monthly_days[key] += 1

        return Response(
            {
                "area": {"slug": area.slug, "name": area.name},
                "state": DataState.AVAILABLE if records else DataState.UNAVAILABLE,
                "source": source_summary(source, dataset="ERA5-Land daily archive (via Open-Meteo)"),
                "start_date": start,
                "end_date": end,
                "retrieved_at": records[-1].retrieved_at if records else None,
                "summary": {
                    "total_mm": round(sum((r.precipitation_mm or 0) for r in records), 2),
                    "wet_days": sum(1 for r in records if (r.precipitation_mm or 0) >= 1),
                    "max_daily_mm": max((r.precipitation_mm or 0) for r in records) if records else None,
                },
                "monthly": [
                    {"month": key, "precipitation_mm": round(value, 2), "days": monthly_days[key]}
                    for key, value in sorted(monthly.items())
                ],
                "daily": WeatherRecordSerializer(records, many=True).data,
                "note": "Historical rainfall is ERA5-Land reanalysis (~9 km), not a single local rain gauge.",
            }
        )
