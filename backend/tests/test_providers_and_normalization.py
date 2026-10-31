from __future__ import annotations

from datetime import UTC, datetime

import pytest
from data_pipelines.normalization.weather import normalize_archive, normalize_forecast
from data_pipelines.providers import cpcb, imd, open_meteo

SAMPLE_FORECAST = {
    "latitude": 22.56,
    "longitude": 88.36,
    "elevation": 6.0,
    "utc_offset_seconds": 19800,
    "timezone": "Asia/Kolkata",
    "current": {
        "time": "2026-06-01T12:00",
        "temperature_2m": 34.5,
        "relative_humidity_2m": 62,
        "apparent_temperature": 41.2,
        "is_day": 1,
        "precipitation": 0.0,
        "weather_code": 1,
        "wind_speed_10m": 12.4,
    },
    "hourly": {
        "time": ["2026-06-01T12:00", "2026-06-01T13:00"],
        "temperature_2m": [34.5, 35.1],
        "precipitation": [0.4, 1.2],
        "precipitation_probability": [55, 70],
        "weather_code": [80, 81],
    },
    "daily": {
        "time": ["2026-06-01"],
        "temperature_2m_max": [36.0],
        "temperature_2m_min": [27.4],
        "precipitation_sum": [8.2],
        "precipitation_probability_max": [80],
        "weather_code": [80],
    },
}


def test_normalize_forecast_preserves_local_times_and_missing_fields():
    normalized = normalize_forecast(SAMPLE_FORECAST)
    current = normalized["current"]
    assert current["kind"] == "CURRENT"
    assert current["valid_time"] == "2026-06-01T12:00:00+05:30"
    assert current["temperature_c"] == 34.5
    assert current["pressure_hpa"] is None
    assert current["is_day"] is True

    assert len(normalized["hourly"]) == 2
    assert normalized["hourly"][1]["precipitation_probability"] == 70
    assert normalized["hourly"][0]["dew_point_c"] is None

    daily = normalized["daily"][0]
    assert daily["kind"] == "DAILY"
    assert daily["valid_time"] == "2026-06-01T00:00:00+05:30"
    assert daily["temperature_max_c"] == 36.0


def test_normalize_archive_returns_daily_values():
    payload = {
        "latitude": 22.56,
        "longitude": 88.36,
        "daily": {
            "time": ["2020-01-01", "2020-01-02"],
            "temperature_2m_mean": [19.4, 20.1],
            "temperature_2m_max": [25.2, 26.0],
            "temperature_2m_min": [14.1, 15.0],
            "precipitation_sum": [0.0, 2.4],
            "relative_humidity_2m_mean": [70.0, 72.0],
            "wind_speed_10m_mean": [8.0, 9.5],
        },
    }
    normalized = normalize_archive(payload)
    assert len(normalized["days"]) == 2
    assert normalized["days"][1]["date"] == "2020-01-02"
    assert normalized["days"][1]["precipitation_mm"] == 2.4


class _Response:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


def test_open_meteo_adapter_builds_bounded_request(monkeypatch):
    captured = {}

    def fake_get(url, params, timeout, headers):
        captured.update(url=url, params=params, timeout=timeout, headers=headers)
        return _Response(payload=SAMPLE_FORECAST)

    monkeypatch.setattr(open_meteo.requests, "get", fake_get)
    result = open_meteo.fetch_forecast(22.56, 88.36, forecast_days=99)
    assert result["latitude"] == 22.56
    assert captured["params"]["forecast_days"] == 16
    assert captured["params"]["timezone"] == "Asia/Kolkata"
    assert "temperature_2m" in captured["params"]["current"]


def test_open_meteo_adapter_raises_provider_error(monkeypatch):
    monkeypatch.setattr(
        open_meteo.requests,
        "get",
        lambda *args, **kwargs: _Response(status_code=429, text="rate limited"),
    )
    with pytest.raises(open_meteo.ProviderError) as error:
        open_meteo.fetch_forecast(22.56, 88.36)
    assert error.value.status_code == 429


def test_imd_requires_key_and_classifies_warnings():
    with pytest.raises(imd.IMDNotConfigured):
        imd.IMDClient(api_key="").district_warnings("WB01")

    assert imd.classify_hazard("Very heavy rainfall expected") == "heavy_rain"
    assert imd.classify_hazard("Heatwave conditions") == "heatwave"
    assert imd.map_severity("orange", "") == "severe"


def test_imd_normalizer_keeps_unmapped_fields_as_partial():
    payload = {
        "data": [
            {
                "warning_id": "WB-1",
                "headline": "Heavy rain warning",
                "message": "Heavy to very heavy rain likely",
                "alert_level": "orange",
                "issued": "2026-06-01T10:00:00+05:30",
                "valid_till": "2026-06-02T10:00:00+05:30",
                "district": "Kolkata",
                "unknown_field": "kept",
            }
        ]
    }
    records = imd.normalize_warnings(payload)
    assert len(records) == 1
    record = records[0]
    assert record["external_id"] == "WB-1"
    assert record["hazard"] == "heavy_rain"
    assert record["severity"] == "severe"
    assert record["quality_status"] == "PARTIAL"
    assert record["raw"]["unknown_field"] == "kept"


def test_cpcb_requires_key_and_groups_pollutants():
    with pytest.raises(cpcb.CPCBNotConfigured):
        cpcb.CPCBClient(api_key="", resource_id="x").fetch_page()

    payload = {
        "records": [
            {
                "station": "Victoria",
                "city": "Kolkata",
                "state": "West Bengal",
                "latitude": "22.55",
                "longitude": "88.35",
                "last_update": "01-06-2026 10:00:00",
                "pollutant_id": "PM2.5",
                "pollutant_avg": "42.5",
                "pollutant_unit": "ug/m3",
            },
            {
                "station": "Victoria",
                "city": "Kolkata",
                "state": "West Bengal",
                "latitude": "22.55",
                "longitude": "88.35",
                "last_update": "01-06-2026 10:00:00",
                "pollutant_id": "PM10",
                "pollutant_avg": "88",
                "pollutant_unit": "ug/m3",
            },
            {
                "station": "No coordinates",
                "city": "Kolkata",
                "last_update": "01-06-2026 10:00:00",
                "pollutant_id": "PM2.5",
                "pollutant_avg": "20",
            },
        ]
    }
    retrieved = datetime(2026, 6, 1, 5, 0, tzinfo=UTC)
    results, warnings = cpcb.normalize_records(payload, retrieved_at=retrieved)
    assert len(results) == 1
    assert results[0]["pollutants"]["pm25"] == 42.5
    assert results[0]["pollutants"]["pm10"] == 88.0
    assert any("coordinates" in warning for warning in warnings)


def test_cpcb_aqi_categories_follow_boundaries():
    assert cpcb.aqi_category(50) == "Good"
    assert cpcb.aqi_category(101) == "Moderate"
    assert cpcb.aqi_category(350) == "Very Poor"
    assert cpcb.aqi_category(450) == "Severe"
