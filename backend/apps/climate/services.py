"""Climate analytics from ERA5-Land daily archive data.

ERA5-Land is a reanalysis dataset with ~9 km native resolution. Metrics are
area-level aggregations, not 1 km observations. The archive is accessed through
Open-Meteo's ERA5-Land archive endpoint (no CDS key required); direct Copernicus
CDS access remains an optional future adapter.
"""

from __future__ import annotations

import logging
from datetime import date
from statistics import mean

from data_pipelines.normalization.weather import normalize_archive
from data_pipelines.providers import open_meteo
from django.conf import settings
from django.utils import timezone

from apps.core.models import DataSource, IngestionRun, IngestionRunStatus
from apps.core.quality import DataState
from apps.locations.models import Area
from apps.weather.models import WeatherLocation

from .models import ClimateBaseline, ClimateMetric, PeriodType

logger = logging.getLogger("apps.climate.ingestion")
DATASET = "era5_land"
RESOLUTION_M = 9000
SEASONS = ("DJF", "MAM", "JJA", "SON")
HOT_DAY_THRESHOLD_C = 35.0
HEAVY_RAIN_THRESHOLD_MM = 50.0


class ClimateIngestionError(Exception):
    pass


def _source() -> DataSource:
    return DataSource.objects.get(slug="era5_land")


def _location(area: Area, source: DataSource) -> WeatherLocation:
    focus_lat, focus_lon = area.focus
    latitude = round(focus_lat, 4)
    longitude = round(focus_lon, 4)
    key = f"{latitude:.4f},{longitude:.4f}"
    location, _ = WeatherLocation.objects.get_or_create(
        source=source,
        provider_location_key=key,
        defaults={
            "area": area,
            "name": f"{area.name} (ERA5-Land point)",
            "point": {"type": "Point", "coordinates": [longitude, latitude]},
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "Asia/Kolkata",
        },
    )
    return location


def _season_for_month(month: int) -> str:
    if month in (12, 1, 2):
        return "DJF"
    if month in (3, 4, 5):
        return "MAM"
    if month in (6, 7, 8):
        return "JJA"
    return "SON"


def _year_stats(days: list[dict], year: int) -> dict:
    in_year = [d for d in days if d["date"].startswith(f"{year}-")]
    complete = len(in_year) >= 360
    temps = [d["temperature_mean_c"] for d in in_year if d["temperature_mean_c"] is not None]
    precip = [d["precipitation_mm"] for d in in_year if d["precipitation_mm"] is not None]
    maxima = [d["temperature_max_c"] for d in in_year if d["temperature_max_c"] is not None]
    stats = {
        "year": year,
        "complete": complete,
        "sample_days": len(in_year),
        "temperature_mean": mean(temps) if temps else None,
        "precipitation_total": sum(precip) if precip else None,
        "hot_days": sum(1 for value in maxima if value >= HOT_DAY_THRESHOLD_C) if maxima else None,
        "heavy_rain_days": sum(1 for value in precip if value >= HEAVY_RAIN_THRESHOLD_MM) if precip else None,
        "seasonal_temperature": {},
    }
    # Meteorological seasons: DJF spans Dec of the previous year and Jan/Feb.
    for season in SEASONS:
        selected = []
        for day in days:
            parsed = date.fromisoformat(day["date"])
            if parsed.month not in _months_for_season(season):
                continue
            if season == "DJF":
                if parsed.month == 12 and parsed.year == year - 1 or parsed.month in (1, 2) and parsed.year == year:
                    selected.append(day)
            elif parsed.year == year:
                selected.append(day)
        values = [d["temperature_mean_c"] for d in selected if d["temperature_mean_c"] is not None]
        expected_days = 90 if season == "DJF" else 92
        if values and len(values) >= expected_days - 8:
            stats["seasonal_temperature"][season] = mean(values)
    return stats


def _months_for_season(season: str) -> set[int]:
    return {"DJF": {12, 1, 2}, "MAM": {3, 4, 5}, "JJA": {6, 7, 8}, "SON": {9, 10, 11}}[season]


def _upsert_baseline(
    source: DataSource,
    *,
    name: str,
    variable: str,
    start_year: int,
    end_year: int,
    value: float,
    unit: str,
    season: str = "",
) -> ClimateBaseline:
    baseline, _ = ClimateBaseline.objects.update_or_create(
        name=name,
        defaults={
            "dataset": DATASET,
            "variable": variable,
            "start_year": start_year,
            "end_year": end_year,
            "value": round(value, 4),
            "unit": unit,
            "spatial_resolution_m": RESOLUTION_M,
            "source": source,
            "metadata": {"season": season, "method": "mean_of_complete_years"},
        },
    )
    return baseline


def ingest_climate(
    area: Area,
    *,
    start_year: int = 1991,
    end_year: int | None = None,
    baseline_start: int = 1991,
    baseline_end: int = 2020,
) -> dict:
    if not settings.OPEN_METEO_ENABLED:
        raise ClimateIngestionError("Open-Meteo is disabled by configuration.")
    source = _source()
    today = timezone.now().date()
    if end_year is None:
        end_year = today.year - 1
    if end_year < start_year:
        raise ClimateIngestionError("end_year must not precede start_year.")
    if baseline_end < baseline_start:
        raise ClimateIngestionError("baseline_end must not precede baseline_start.")

    run = IngestionRun.objects.create(
        source=source,
        status=IngestionRunStatus.RUNNING,
        params={
            "area": area.slug,
            "start_year": start_year,
            "end_year": end_year,
            "baseline_start": baseline_start,
            "baseline_end": baseline_end,
            "dataset": DATASET,
        },
    )
    try:
        location = _location(area, source)
        payload = open_meteo.fetch_archive(
            location.latitude,
            location.longitude,
            start_date=f"{start_year}-01-01",
            end_date=f"{end_year}-12-31",
            timezone="Asia/Kolkata",
            timeout=120,
        )
        normalized = normalize_archive(payload, timezone="Asia/Kolkata")
        days = normalized["days"]
        if not days:
            raise ClimateIngestionError("ERA5-Land archive returned no daily records.")

        years = list(range(start_year, end_year + 1))
        stats = [_year_stats(days, year) for year in years]
        complete_stats = [s for s in stats if s["complete"] and s["temperature_mean"] is not None]
        if len(complete_stats) < 3:
            raise ClimateIngestionError("Insufficient complete years for a meaningful climate analysis.")

        baseline_stats = [
            s for s in stats if baseline_start <= s["year"] <= baseline_end and s["complete"]
        ]
        if not baseline_stats:
            raise ClimateIngestionError("No complete years fall inside the requested baseline period.")

        temp_baseline = _upsert_baseline(
            source,
            name=f"{area.slug} ERA5-Land {baseline_start}-{baseline_end} annual mean temperature",
            variable="temperature_2m_mean_annual",
            start_year=baseline_start,
            end_year=baseline_end,
            value=mean(s["temperature_mean"] for s in baseline_stats),
            unit="°C",
        )
        precip_stats = [s for s in baseline_stats if s["precipitation_total"] is not None]
        precip_baseline = _upsert_baseline(
            source,
            name=f"{area.slug} ERA5-Land {baseline_start}-{baseline_end} annual precipitation",
            variable="precipitation_sum_annual",
            start_year=baseline_start,
            end_year=baseline_end,
            value=mean(s["precipitation_total"] for s in precip_stats),
            unit="mm",
        )
        hot_stats = [s for s in baseline_stats if s["hot_days"] is not None]
        hot_baseline = (
            _upsert_baseline(
                source,
                name=f"{area.slug} ERA5-Land {baseline_start}-{baseline_end} hot days (>=35°C)",
                variable="hot_days_ge_35c_annual",
                start_year=baseline_start,
                end_year=baseline_end,
                value=mean(s["hot_days"] for s in hot_stats),
                unit="days",
            )
            if hot_stats
            else None
        )

        seasonal_baselines: dict[str, ClimateBaseline] = {}
        for season in SEASONS:
            values = [
                s["seasonal_temperature"][season]
                for s in baseline_stats
                if season in s["seasonal_temperature"]
            ]
            if values:
                seasonal_baselines[season] = _upsert_baseline(
                    source,
                    name=f"{area.slug} ERA5-Land {baseline_start}-{baseline_end} {season} mean temperature",
                    variable="temperature_2m_mean_seasonal",
                    start_year=baseline_start,
                    end_year=baseline_end,
                    value=mean(values),
                    unit="°C",
                    season=season,
                )

        written = 0
        base_metadata = {
            "dataset": DATASET,
            "native_resolution_m": RESOLUTION_M,
            "method": "area point aggregation from ERA5-Land daily values",
            "provider": "Open-Meteo archive API",
        }
        for stat in stats:
            if not stat["complete"] or stat["temperature_mean"] is None:
                continue
            year = stat["year"]
            period_start = date(year, 1, 1)
            period_end = date(year, 12, 31)
            metrics = [
                (
                    "temperature_2m_mean",
                    PeriodType.ANNUAL,
                    "",
                    stat["temperature_mean"],
                    "°C",
                    temp_baseline,
                    "mean_daily_temperature",
                ),
                (
                    "precipitation_sum",
                    PeriodType.ANNUAL,
                    "",
                    stat["precipitation_total"],
                    "mm",
                    precip_baseline,
                    "sum_daily_precipitation",
                ),
                (
                    "hot_days_ge_35c",
                    PeriodType.ANNUAL,
                    "",
                    stat["hot_days"],
                    "days",
                    hot_baseline,
                    "days_with_max_temperature_at_or_above_35c",
                ),
                (
                    "heavy_rain_days_ge_50mm",
                    PeriodType.ANNUAL,
                    "",
                    stat["heavy_rain_days"],
                    "days",
                    None,
                    "days_with_daily_precipitation_at_or_above_50mm",
                ),
            ]
            for variable, period_type, season, value, unit, baseline, method in metrics:
                if value is None:
                    continue
                anomaly = round(value - baseline.value, 4) if baseline else None
                ClimateMetric.objects.update_or_create(
                    source=source,
                    area=area,
                    dataset=DATASET,
                    variable=variable,
                    period_type=period_type,
                    season=season,
                    period_start=period_start,
                    defaults={
                        "period_end": period_end,
                        "value": round(float(value), 4),
                        "unit": unit,
                        "anomaly": anomaly,
                        "baseline": baseline,
                        "spatial_resolution_m": RESOLUTION_M,
                        "quality_status": DataState.AVAILABLE,
                        "metadata": {
                            **base_metadata,
                            "sample_days": stat["sample_days"],
                            "method": method,
                            "season": season,
                        },
                    },
                )
                written += 1

            for season, value in stat["seasonal_temperature"].items():
                baseline = seasonal_baselines.get(season)
                ClimateMetric.objects.update_or_create(
                    source=source,
                    area=area,
                    dataset=DATASET,
                    variable="temperature_2m_mean",
                    period_type=PeriodType.SEASONAL,
                    season=season,
                    period_start=period_start,
                    defaults={
                        "period_end": period_end,
                        "value": round(value, 4),
                        "unit": "°C",
                        "anomaly": round(value - baseline.value, 4) if baseline else None,
                        "baseline": baseline,
                        "spatial_resolution_m": RESOLUTION_M,
                        "quality_status": DataState.AVAILABLE,
                        "metadata": {**base_metadata, "season": season, "method": "seasonal_mean"},
                    },
                )
                written += 1

        run.status = IngestionRunStatus.SUCCESS
        run.records_fetched = len(days)
        run.records_written = written
        run.finished_at = timezone.now()
        run.save(update_fields=["status", "records_fetched", "records_written", "finished_at"])
        return {
            "written": written,
            "years": len(complete_stats),
            "baseline_years": len(baseline_stats),
            "run_id": str(run.id),
        }
    except Exception as exc:  # noqa: BLE001
        run.status = IngestionRunStatus.FAILED
        run.finished_at = timezone.now()
        run.error_message = str(exc)[:2000]
        run.save(update_fields=["status", "finished_at", "error_message"])
        logger.exception("Climate ingestion failed")
        raise ClimateIngestionError(str(exc)) from exc
