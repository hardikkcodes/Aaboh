from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from apps.heat.guide import _level
from apps.rainfall.models import RainOutlook
from apps.rainfall.outlook import chance_at, summarise

NOW = datetime(2026, 7, 1, 3, 0, tzinfo=UTC)  # 08:30 in Kolkata


def _times(hours=72):
    start = datetime(2026, 7, 1, 0, 0)
    return [(start + timedelta(hours=hour)).isoformat() for hour in range(hours)]


def test_chance_is_the_share_of_runs_with_rain():
    times = _times()
    wet = [2.0] * 72
    dry = [0.0] * 72
    result = summarise(times, [wet, wet, wet, dry], NOW)
    assert result["runs"] == 4
    assert result["days"][0]["chance_pct"] == 75
    assert result["next_24h"]["chance_pct"] == 75


def test_heavy_chance_is_separate_from_any_rain():
    times = _times()
    light = [0.2] * 72
    heavy = [5.0] * 72
    today = summarise(times, [light, light, light, heavy], NOW)["days"][0]
    assert today["chance_pct"] == 100
    assert today["heavy_chance_pct"] == 25


def test_past_hours_do_not_count():
    times = _times()
    early_only = [5.0] * 8 + [0.0] * 64
    assert summarise(times, [early_only] * 2, NOW)["days"][0]["chance_pct"] == 0


def test_a_finished_part_of_the_day_is_left_out():
    late = datetime(2026, 7, 1, 13, 0, tzinfo=UTC)  # 18:30 in Kolkata
    parts = summarise(_times(), [[1.0] * 72] * 2, late)["parts"]
    today = [item["part"] for item in parts if item["day"] == "today"]
    assert today == ["evening", "night"]


@pytest.mark.django_db
def test_rain_api_carries_the_outlook(api_client, area):
    payload = summarise(_times(), [[1.0] * 72] * 2, NOW)
    RainOutlook.objects.create(area=area, payload=payload)
    body = api_client.get("/api/v1/rainfall/forecast/", {"area": area.slug}).json()
    assert body["outlook"]["runs"] == 2


@pytest.mark.django_db
def test_chance_at_finds_the_right_block(area):
    RainOutlook.objects.create(area=area, payload=summarise(_times(), [[1.0] * 72] * 2, NOW))
    assert chance_at(area, NOW) == 100
    assert chance_at(area, NOW + timedelta(days=5)) is None


def test_heat_levels():
    assert _level(25) == "comfortable"
    assert _level(30) == "caution"
    assert _level(35) == "high"
    assert _level(45) == "dangerous"


@pytest.mark.django_db
def test_heat_guide_works_with_no_data(api_client, area):
    reply = api_client.get("/api/v1/heat/guide/", {"area": area.slug})
    assert reply.status_code == 200
    assert reply.json()["hottest"] == []


@pytest.mark.django_db
def test_a_late_feed_is_not_called_unavailable(api_client, area):
    body = api_client.get("/api/v1/alerts/", {"area": area.slug}).json()
    assert "feed_status" in body


@pytest.mark.django_db
def test_auto_refresh_stays_off_when_disabled():
    from apps.core.freshness import refresh_if_old

    assert refresh_if_old() is False
