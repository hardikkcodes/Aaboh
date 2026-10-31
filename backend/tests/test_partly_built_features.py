from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from data_pipelines.providers.gdacs import parse_events
from django.utils import timezone

from apps.accounts.models import SavedRoute, UserPreference
from apps.alerts.cyclones import active_cyclones
from apps.alerts.models import TropicalCyclone
from apps.environment.models import CellTerrain
from apps.intelligence.scorecard import _share_below
from apps.notifications.models import Notification, NotificationKind
from apps.notifications.services import commute_nudge

IST = ZoneInfo("Asia/Kolkata")


def _feature(longitude, latitude, current="true"):
    return {
        "geometry": {"coordinates": [longitude, latitude]},
        "properties": {
            "eventid": 7,
            "eventname": "REMAL",
            "alertlevel": "Orange",
            "iscurrent": current,
            "url": {"report": "https://www.gdacs.org/report"},
        },
    }


def test_only_current_storms_in_our_basin_are_kept():
    payload = {"features": [_feature(89, 18), _feature(142, 22), _feature(89, 18, current="false")]}
    storms = parse_events(payload)
    assert [storm["name"] for storm in storms] == ["REMAL"]


@pytest.mark.django_db
def test_an_old_cyclone_read_is_not_shown():
    storm = TropicalCyclone.objects.create(event_id="1", name="OLD", latitude=18, longitude=89, distance_km=500)
    assert active_cyclones()
    assert not active_cyclones(now=timezone.now() + timedelta(hours=7))
    assert storm.name == "OLD"


@pytest.mark.django_db
def test_cyclone_api_is_public(api_client):
    TropicalCyclone.objects.create(event_id="1", name="REMAL", latitude=18, longitude=89, distance_km=500)
    body = api_client.get("/api/v1/cyclones/").json()
    assert body["results"][0]["name"] == "REMAL"


def test_share_below_needs_enough_cells():
    assert _share_below({"a": 1, "b": 2}, "b") is None
    values = {str(number): number for number in range(10)}
    assert _share_below(values, "5") == 50


class _Hour:
    def __init__(self, when, chance, amount):
        self.valid_time, self.precipitation_probability, self.precipitation_mm = when, chance, amount


def _departure(minutes_ahead):
    now = datetime(2026, 7, 1, 7, 0, tzinfo=IST)
    return now, (now + timedelta(minutes=minutes_ahead)).time()


def test_nudge_when_rain_is_likely_near_leaving_time():
    now, leave_at = _departure(60)
    assert commute_nudge(leave_at, [_Hour(now + timedelta(hours=1), 80, 2.0)], now) is not None


def test_no_nudge_when_dry_or_too_early():
    now, leave_at = _departure(60)
    assert commute_nudge(leave_at, [_Hour(now + timedelta(hours=1), 5, 0.0)], now) is None
    now, leave_at = _departure(300)
    assert commute_nudge(leave_at, [_Hour(now + timedelta(hours=5), 90, 5.0)], now) is None


@pytest.mark.django_db
def test_route_keeps_a_leaving_time(auth_client):
    reply = auth_client.post(
        "/api/v1/users/me/routes/",
        {"label": "College", "points": [[22.5, 88.3], [22.6, 88.4]], "leave_at": "08:30"},
        format="json",
    )
    assert reply.status_code == 201
    assert reply.json()["leave_at"].startswith("08:30")
    assert SavedRoute.objects.get().leave_at == time(8, 30)


def test_models_are_importable():
    assert CellTerrain and Notification and NotificationKind.ROUTE_RAIN and UserPreference
