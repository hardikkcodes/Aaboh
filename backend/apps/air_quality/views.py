from __future__ import annotations

from datetime import timedelta

from django.db.models import Prefetch
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.geometry import haversine_m
from apps.core.models import DataSource
from apps.core.quality import source_availability
from apps.core.serializers import source_summary
from apps.locations.models import Area

from .models import AQIMeasurement, AQIStation
from .serializers import AQIMeasurementSerializer, AQIStationSerializer


class AirQualityStationsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        source = DataSource.objects.filter(slug="cpcb").first()
        availability = source_availability(source) if source else {"state": "UNAVAILABLE"}
        now = timezone.now()
        measurements = AQIMeasurement.objects.filter(measured_at__gte=now - timedelta(days=7)).order_by(
            "-measured_at"
        )
        stations = list(
            AQIStation.objects.filter(is_active=True)
            .select_related("source")
            .prefetch_related(Prefetch("measurements", queryset=measurements, to_attr="latest_measurements"))
        )

        latitude = request.query_params.get("lat")
        longitude = request.query_params.get("lon")
        if latitude is None or longitude is None:
            area_slug = request.query_params.get("area", "kolkata")
            area = Area.objects.filter(slug=area_slug).first()
            if area:
                latitude, longitude = str(area.centroid_lat), str(area.centroid_lon)
        if latitude is not None and longitude is not None:
            try:
                lat_f, lon_f = float(latitude), float(longitude)
            except ValueError as exc:
                raise ValidationError({"lat": "Latitude and longitude must be numeric."}) from exc
            for station in stations:
                station.distance_km = round(haversine_m(lat_f, lon_f, station.latitude, station.longitude) / 1000, 2)
            stations.sort(key=lambda s: s.distance_km)
            nearest_only = request.query_params.get("nearest", "false").lower() == "true"
            if nearest_only and stations:
                stations = stations[:1]

        has_measurement = any(getattr(s, "latest_measurements", None) for s in stations)
        state = availability["state"] if has_measurement else "UNAVAILABLE"
        if has_measurement and state == "UNAVAILABLE":
            state = "STALE"
        return Response(
            {
                "state": state,
                "count": len(stations),
                "source": source_summary(source) if source else {},
                "last_success_at": availability.get("last_success_at"),
                "results": AQIStationSerializer(stations, many=True).data,
                "note": (
                    "Measurements are station observations. Station values are not interpolated into "
                    "a neighbourhood AQI surface."
                ),
                "reason": (
                    "CPCB_API_KEY is not configured; station measurements are unavailable."
                    if not has_measurement
                    else None
                ),
            }
        )


class AirQualityMeasurementsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        queryset = AQIMeasurement.objects.select_related("station", "source")
        station_id = request.query_params.get("station")
        if station_id:
            queryset = queryset.filter(station_id=station_id)
        station_name = request.query_params.get("station_name")
        if station_name:
            queryset = queryset.filter(station__name__icontains=station_name)
        try:
            hours = min(max(int(request.query_params.get("hours", 24)), 1), 24 * 90)
        except ValueError as exc:
            raise ValidationError({"hours": "Must be an integer."}) from exc
        since = timezone.now() - timedelta(hours=hours)
        queryset = queryset.filter(measured_at__gte=since).order_by("-measured_at")[:500]
        return Response(
            {
                "state": "AVAILABLE" if queryset else "UNAVAILABLE",
                "count": len(queryset),
                "results": AQIMeasurementSerializer(queryset, many=True).data,
                "note": "Station measurement time and source are preserved for every record.",
            }
        )
