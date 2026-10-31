from __future__ import annotations

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.models import DataSource
from apps.core.quality import source_availability
from apps.core.schemas import DocumentedAPIView
from apps.core.serializers import source_summary
from apps.locations.models import Area

from .models import ClimateMetric, PeriodType
from .serializers import ClimateMetricSerializer


def _area(request) -> Area:
    slug = request.query_params.get("area", "kolkata")
    try:
        return Area.objects.get(slug=slug, is_active=True)
    except Area.DoesNotExist as exc:
        raise ValidationError({"area": f"Unknown area: {slug}"}) from exc


def _linear_trend(series: list[dict]) -> dict | None:
    points = [(int(item["year"]), float(item["value"])) for item in series if item.get("value") is not None]
    if len(points) < 5:
        return None
    n = len(points)
    sum_x = sum(x for x, _ in points)
    sum_y = sum(y for _, y in points)
    sum_xy = sum(x * y for x, y in points)
    sum_xx = sum(x * x for x, _ in points)
    denominator = n * sum_xx - sum_x * sum_x
    if denominator == 0:
        return None
    slope = (n * sum_xy - sum_x * sum_y) / denominator
    return {
        "slope_per_decade": round(slope * 10, 4),
        "start_year": points[0][0],
        "end_year": points[-1][0],
        "n_years": n,
        "method": "ordinary least squares on annual values",
        "caveat": "A short record and autocorrelation limit causal interpretation.",
    }


class ClimateMetricsView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        area = _area(request)
        queryset = ClimateMetric.objects.filter(area=area).select_related("baseline", "source")
        variable = request.query_params.get("variable")
        period_type = request.query_params.get("period_type")
        season = request.query_params.get("season")
        year = request.query_params.get("year")
        if variable:
            queryset = queryset.filter(variable=variable)
        if period_type:
            queryset = queryset.filter(period_type=period_type)
        if season:
            queryset = queryset.filter(season=season)
        if year:
            try:
                queryset = queryset.filter(period_start__year=int(year))
            except ValueError as exc:
                raise ValidationError({"year": "Must be an integer."}) from exc
        metrics = list(queryset.order_by("period_start", "variable", "season"))
        source = DataSource.objects.filter(slug="era5_land").first()
        return Response(
            {
                "area": {"slug": area.slug, "name": area.name},
                "state": "AVAILABLE" if metrics else "UNAVAILABLE",
                "source": source_summary(source, dataset="ERA5-Land") if source else {},
                "source_state": source_availability(source)["state"] if source else "UNAVAILABLE",
                "count": len(metrics),
                "results": ClimateMetricSerializer(metrics, many=True).data,
                "note": (
                    "ERA5-Land has ~9 km native resolution. These are area-level reanalysis metrics, "
                    "not 1 km observations."
                ),
                "reason": None if metrics else "No climate metrics have been ingested for this area.",
            }
        )


class ClimateTrendsView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        area = _area(request)
        metrics = list(ClimateMetric.objects.filter(area=area).select_related("baseline", "source"))
        source = DataSource.objects.filter(slug="era5_land").first()
        if not metrics:
            return Response(
                {
                    "area": {"slug": area.slug, "name": area.name},
                    "state": "UNAVAILABLE",
                    "source": source_summary(source, dataset="ERA5-Land") if source else {},
                    "series": {},
                    "reason": (
                        "No ERA5-Land climate metrics are available. Run: python manage.py fetch_climate --area "
                        f"{area.slug}"
                    ),
                    "methodology": (
                        "ERA5-Land daily values are aggregated to annual and seasonal metrics. "
                        "The 1991-2020 baseline is calculated from complete years only."
                    ),
                }
            )

        def series_for(variable: str, period_type: str = PeriodType.ANNUAL, season: str = "") -> list[dict]:
            selected = [
                m
                for m in metrics
                if m.variable == variable and m.period_type == period_type and m.season == season
            ]
            selected.sort(key=lambda m: m.period_start)
            return [
                {
                    "year": m.period_start.year,
                    "value": m.value,
                    "anomaly": m.anomaly,
                    "unit": m.unit,
                    "period_start": m.period_start,
                    "period_end": m.period_end,
                    "baseline_value": m.baseline.value if m.baseline else None,
                }
                for m in selected
            ]

        annual_temperature = series_for("temperature_2m_mean")
        annual_precipitation = series_for("precipitation_sum")
        hot_days = series_for("hot_days_ge_35c")
        heavy_rain = series_for("heavy_rain_days_ge_50mm")
        seasonal_temperature = {
            season: series_for("temperature_2m_mean", PeriodType.SEASONAL, season)
            for season in ("DJF", "MAM", "JJA", "SON")
        }
        seasonal_temperature = {k: v for k, v in seasonal_temperature.items() if v}

        baselines = {}
        for metric in metrics:
            if metric.baseline and metric.baseline.name not in baselines:
                baselines[metric.baseline.name] = {
                    "name": metric.baseline.name,
                    "start_year": metric.baseline.start_year,
                    "end_year": metric.baseline.end_year,
                    "value": metric.baseline.value,
                    "unit": metric.baseline.unit,
                    "variable": metric.baseline.variable,
                }

        return Response(
            {
                "area": {"slug": area.slug, "name": area.name},
                "state": "AVAILABLE",
                "source": source_summary(source, dataset="ERA5-Land") if source else {},
                "dataset": {
                    "name": "ERA5-Land reanalysis",
                    "native_resolution_m": 9000,
                    "provider_access": "Open-Meteo archive API",
                    "note": "Do not interpret these series as 1 km local observations.",
                },
                "series": {
                    "annual_temperature": annual_temperature,
                    "annual_precipitation": annual_precipitation,
                    "hot_days_ge_35c": hot_days,
                    "heavy_rain_days_ge_50mm": heavy_rain,
                    "seasonal_temperature": seasonal_temperature,
                },
                "trends": {
                    "annual_temperature": _linear_trend(annual_temperature),
                    "annual_precipitation": _linear_trend(annual_precipitation),
                    "hot_days_ge_35c": _linear_trend(hot_days),
                    "seasonal_temperature": {
                        season: _linear_trend(series)
                        for season, series in seasonal_temperature.items()
                    },
                },
                "baselines": list(baselines.values()),
                "methodology": (
                    "Annual metrics use complete calendar years from ERA5-Land daily values. "
                    "Temperature anomaly = annual mean minus the 1991-2020 annual mean. "
                    "Hot days count days with maximum temperature >= 35°C. "
                    "Heavy-rain days count daily precipitation >= 50 mm. "
                    "Trends are descriptive ordinary-least-squares slopes, not causal attribution."
                ),
            }
        )
