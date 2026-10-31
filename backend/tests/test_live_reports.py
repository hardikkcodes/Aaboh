"""Live city map, fast reporting, confirmations and expiry."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.geometry import point_geojson
from apps.incidents.models import IncidentConfirmation, IncidentReport, IncidentStatus
from apps.incidents.services import create_incident
from apps.intelligence.place_status import build_place_status
from apps.intelligence.services import generate_insights

pytestmark = pytest.mark.django_db

LIVE_URL = "/api/v1/incidents/live/"


@pytest.fixture(autouse=True)
def clear_rate_limits():
    cache.clear()
    yield
    cache.clear()


def resident(name: str) -> APIClient:
    user = get_user_model().objects.create_user(
        username=name, email=f"{name}@example.com", password="a-very-long-password-123"
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_report(area, reporter=None, *, category="waterlogging", **overrides) -> IncidentReport:
    report = create_incident(
        reporter=reporter,
        area=area,
        category=category,
        occurred_at=timezone.now() - timedelta(minutes=20),
        latitude=22.553123,
        longitude=88.352456,
    )
    if overrides:
        IncidentReport.objects.filter(pk=report.pk).update(**overrides)
        report.refresh_from_db()
    return report


def confirm(client: APIClient, report: IncidentReport, kind: str):
    return client.post(f"/api/v1/incidents/{report.id}/confirm/", {"kind": kind}, format="json")


def live_ids(client: APIClient) -> list[str]:
    return [feature["properties"]["id"] for feature in client.get(LIVE_URL).json()["features"]]


def test_fast_report_needs_only_type_location_and_depth(auth_client, area, neighbourhood):
    response = auth_client.post(
        "/api/v1/incidents/",
        {
            "area": area.slug,
            "category": "waterlogging",
            "occurred_at": timezone.now().isoformat(),
            "latitude": 22.553,
            "longitude": 88.352,
            "water_depth": "knee",
            "passability": "two_wheeler",
        },
        format="json",
    )

    assert response.status_code == 201, response.content
    body = response.json()
    assert body["water_depth_label"] == "Knee deep"
    assert body["trust"] == "unconfirmed"
    assert body["is_active"] is True
    assert body["neighbourhood"]["slug"] == neighbourhood.slug


def test_depth_is_rejected_for_non_water_reports(auth_client, area, incident_payload):
    response = auth_client.post(
        "/api/v1/incidents/",
        {**incident_payload, "category": "power_cut", "neighbourhood": "", "water_depth": "knee"},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    ("category", "hours"),
    [("waterlogging", 6), ("power_cut", 6), ("fallen_tree", 24), ("stagnant_water", 168)],
)
def test_reports_expire_by_type(area, category, hours):
    report = make_report(area, category=category)
    assert report.expires_at == report.occurred_at + timedelta(hours=hours)


def test_live_map_shows_only_current_public_reports(api_client, area):
    active = make_report(area)
    make_report(area, expires_at=timezone.now() - timedelta(minutes=1))
    make_report(area, is_public=False)
    make_report(area, cleared_at=timezone.now())
    make_report(area, status=IncidentStatus.REJECTED)
    make_report(area, status=IncidentStatus.RESOLVED)

    assert live_ids(api_client) == [str(active.id)]


def test_live_map_filters_and_rounds_coordinates(api_client, area):
    make_report(area)
    tree = make_report(area, category="fallen_tree")

    body = api_client.get(LIVE_URL, {"category": "fallen_tree"}).json()

    assert [item["properties"]["id"] for item in body["features"]] == [str(tree.id)]
    assert body["features"][0]["geometry"]["coordinates"] == [88.3525, 22.5531]
    assert "reporter" not in body["features"][0]["properties"]
    assert api_client.get(LIVE_URL, {"category": "nonsense"}).status_code == 400


def test_confirmation_requires_sign_in(api_client, area):
    assert confirm(api_client, make_report(area), "still_there").status_code in {401, 403}


def test_two_other_residents_confirm_a_report(area, user, auth_client):
    report = make_report(area, reporter=user)

    assert confirm(auth_client, report, "still_there").status_code == 400

    first = confirm(resident("one"), report, "still_there").json()
    assert first["trust"] == "unconfirmed"
    second = confirm(resident("two"), report, "still_there").json()
    assert second["trust"] == "resident_confirmed"
    assert second["verification_state"] == "UNVERIFIED"


def test_one_person_has_one_vote_and_can_change_it(area):
    report = make_report(area)
    client = resident("one")

    confirm(client, report, "still_there")
    confirm(client, report, "still_there")
    body = confirm(client, report, "wrong").json()

    assert IncidentConfirmation.objects.count() == 1
    assert body["confirmations"] == {"still_there": 0, "cleared": 0, "wrong": 1}


def test_moderator_verification_is_kept_separate(area, moderator_client):
    report = make_report(area)
    confirm(resident("one"), report, "still_there")
    confirm(resident("two"), report, "still_there")

    body = moderator_client.post(
        f"/api/v1/incidents/{report.id}/moderate/", {"status": "VERIFIED"}, format="json"
    ).json()

    assert body["trust"] == "moderator_verified"


def test_still_there_extends_but_is_capped(area):
    report = make_report(area, expires_at=timezone.now() + timedelta(minutes=5))

    extended = confirm(resident("one"), report, "still_there").json()
    report.refresh_from_db()
    assert extended["is_active"] is True
    assert report.expires_at > timezone.now() + timedelta(hours=5)

    old = make_report(
        area,
        occurred_at=timezone.now() - timedelta(hours=23),
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    confirm(resident("two"), old, "still_there")
    old.refresh_from_db()
    assert old.expires_at <= old.occurred_at + timedelta(hours=24)


def test_one_cleared_vote_does_not_remove_a_report(api_client, area):
    report = make_report(area)

    confirm(resident("one"), report, "cleared")
    assert live_ids(api_client) == [str(report.id)]

    confirm(resident("two"), report, "cleared")
    assert live_ids(api_client) == []


@pytest.mark.parametrize("who", ["reporter", "moderator"])
def test_reporter_or_moderator_can_clear_at_once(api_client, area, user, auth_client, moderator_client, who):
    report = make_report(area, reporter=user)
    client = auth_client if who == "reporter" else moderator_client

    assert confirm(client, report, "cleared").status_code == 200
    assert live_ids(api_client) == []


def test_inactive_and_hidden_reports_cannot_be_confirmed(area):
    client = resident("one")
    expired = make_report(area, expires_at=timezone.now() - timedelta(minutes=1))
    hidden = make_report(area, is_public=False)

    assert confirm(client, expired, "still_there").status_code == 400
    assert confirm(client, hidden, "still_there").status_code == 404


def test_cleared_reports_stop_raising_risk(area):
    IncidentReport.objects.create(
        area=area,
        category="waterlogging",
        occurred_at=timezone.now() - timedelta(hours=1),
        point=point_geojson(22.553, 88.352),
        latitude=22.553,
        longitude=88.352,
        status=IncidentStatus.VERIFIED,
        cleared_at=timezone.now(),
    )

    assert build_place_status(area)["waterlogging"]["reports"]["verified"] == 0
    rules = [item["rule_id"] for item in generate_insights(area)["insights"]]
    assert "verified_waterlogging" not in rules
