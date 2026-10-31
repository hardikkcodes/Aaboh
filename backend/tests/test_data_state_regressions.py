"""Regressions for secret exposure and misleading official-alert states."""

from __future__ import annotations

from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from apps.air_quality.services import AirQualityIngestionError, ingest_cpcb
from apps.alerts import services as alert_services
from apps.alerts.models import OfficialAlert
from apps.core.models import DataSource, IngestionRun, IngestionRunStatus
from apps.core.quality import DataState, source_availability
from apps.intelligence.place_status import build_place_status

pytestmark = pytest.mark.django_db


def sachet_run(status: str, *, age: timedelta = timedelta(0)) -> IngestionRun:
    run = IngestionRun.objects.create(
        source=DataSource.objects.get(slug="sachet"),
        status=status,
        finished_at=None if status == IngestionRunStatus.RUNNING else timezone.now(),
    )
    IngestionRun.objects.filter(pk=run.pk).update(started_at=timezone.now() - age)
    return run


def test_cpcb_key_is_not_exposed_after_a_network_failure(settings, api_client, area):
    settings.CPCB_API_KEY = "test-secret-key"
    settings.CPCB_BASE_URL = "http://127.0.0.1:9/resource"
    settings.CPCB_TIMEOUT = 1

    with mock.patch("data_pipelines.providers.cpcb.time.sleep"), pytest.raises(AirQualityIngestionError):
        ingest_cpcb(max_pages=1, cities=["Kolkata"])

    assert "test-secret-key" not in IngestionRun.objects.get(source__slug="cpcb").error_message
    for path in ("/api/v1/system/data-status/", "/api/v1/air-quality/stations/"):
        assert "test-secret-key" not in api_client.get(path).content.decode()


def test_provider_error_text_is_not_returned_publicly(api_client, area):
    run = sachet_run(IngestionRunStatus.FAILED)
    IngestionRun.objects.filter(pk=run.pk).update(error_message="internal-provider-detail")

    assert "last_error" not in source_availability(DataSource.objects.get(slug="sachet"))
    for path in ("/api/v1/system/data-status/", "/api/v1/alerts/"):
        assert "internal-provider-detail" not in api_client.get(path).content.decode()


def test_failed_latest_fetch_is_not_reported_as_reachable(api_client, area):
    sachet_run(IngestionRunStatus.SUCCESS, age=timedelta(minutes=2))
    sachet_run(IngestionRunStatus.FAILED)

    body = api_client.get("/api/v1/alerts/").json()

    assert body["state"] == DataState.STALE
    assert "reachable" not in body["feed_message"]


def test_crashed_ingest_is_recorded_as_failed(api_client, area):
    with (
        mock.patch.object(alert_services, "SACHETClient") as client,
        mock.patch.object(alert_services, "_upsert_alerts", side_effect=RuntimeError("database failed")),
    ):
        client.return_value.fetch_all.return_value = []
        with pytest.raises(alert_services.AlertIngestionError):
            alert_services.ingest_sachet_alerts()

    assert IngestionRun.objects.get(source__slug="sachet").status == IngestionRunStatus.FAILED
    assert "reachable" not in api_client.get("/api/v1/alerts/").json()["feed_message"]


def test_abandoned_run_is_not_reported_as_healthy(api_client, area):
    sachet_run(IngestionRunStatus.SUCCESS, age=timedelta(hours=2))
    sachet_run(IngestionRunStatus.RUNNING, age=timedelta(hours=1))

    source = DataSource.objects.get(slug="sachet")

    assert source_availability(source)["state"] == DataState.STALE
    assert "reachable" not in api_client.get("/api/v1/alerts/").json()["feed_message"]


def test_refresh_in_progress_keeps_the_last_completed_state():
    sachet_run(IngestionRunStatus.SUCCESS, age=timedelta(minutes=2))
    sachet_run(IngestionRunStatus.RUNNING)

    assert source_availability(DataSource.objects.get(slug="sachet"))["state"] == DataState.AVAILABLE


def test_active_alert_survives_missing_weather_and_reports(area):
    now = timezone.now()
    OfficialAlert.objects.create(
        source=DataSource.objects.get(slug="sachet"),
        external_id="alert-1",
        title="Extreme rain warning",
        severity="extreme",
        issued_at=now,
        retrieved_at=now,
        expires_at=now + timedelta(hours=6),
        areas_text="Kolkata",
    )

    status = build_place_status(area)["status"]

    assert status["level"] == "attention"
    assert status["headline"] == "Official warning in effect"
    assert any("official warning" in reason for reason in status["reasons"])
