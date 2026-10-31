from __future__ import annotations

import pytest
import requests

from apps.locations import google_maps
from apps.locations.models import Neighbourhood

pytestmark = pytest.mark.django_db


class Reply:
    def __init__(self, payload, status_code=200):
        self.payload, self.status_code = payload, status_code

    def json(self):
        return self.payload


def test_polyline_decodes():
    assert google_maps.decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@") == [
        [38.5, -120.2],
        [40.7, -120.95],
        [43.252, -126.453],
    ]


def test_long_routes_are_thinned_and_keep_both_ends():
    points = [[index, index] for index in range(500)]
    thinned = google_maps.thin(points)
    assert len(thinned) == google_maps.MAX_ROUTE_POINTS
    assert thinned[0] == points[0] and thinned[-1] == points[-1]


def test_search_uses_local_places_without_a_key(api_client, area, settings):
    settings.GOOGLE_MAPS_API_KEY = ""
    Neighbourhood.objects.create(
        area=area, slug="behala", name="Behala", point={"type": "Point", "coordinates": [88.3, 22.5]},
        latitude=22.5, longitude=88.3,
    )
    body = api_client.get("/api/v1/places/autocomplete/", {"q": "beh"}).json()
    assert body["provider"] == "local"
    assert body["results"][0]["latitude"] == 22.5


def test_search_uses_google_when_a_key_is_set(api_client, settings, monkeypatch):
    settings.GOOGLE_MAPS_API_KEY = "test-value"
    suggestion = {
        "placePrediction": {
            "placeId": "abc",
            "text": {"text": "Jadavpur University, Kolkata"},
            "structuredFormat": {"mainText": {"text": "Jadavpur University"}, "secondaryText": {"text": "Kolkata"}},
        }
    }
    monkeypatch.setattr(requests, "request", lambda *a, **k: Reply({"suggestions": [suggestion]}))
    body = api_client.get("/api/v1/places/autocomplete/", {"q": "jadav", "session": "s"}).json()
    assert body["provider"] == "google"
    assert body["results"][0] == {"place_id": "abc", "title": "Jadavpur University", "subtitle": "Kolkata"}


def test_google_failure_falls_back_without_exposing_details(api_client, settings, monkeypatch):
    settings.GOOGLE_MAPS_API_KEY = "secret-value"

    def fail(*args, **kwargs):
        raise requests.ConnectionError("https://example.test?key=secret-value")

    monkeypatch.setattr(requests, "request", fail)
    reply = api_client.get("/api/v1/places/autocomplete/", {"q": "jadav"})
    assert reply.status_code == 200
    assert "secret-value" not in reply.content.decode()
    assert reply.json()["provider"] == "local"


def test_route_planning_needs_a_key(auth_client, settings):
    settings.GOOGLE_MAPS_API_KEY = ""
    reply = auth_client.post(
        "/api/v1/routes/plan/", {"origin": [22.5, 88.3], "destination": [22.6, 88.4]}, format="json"
    )
    assert reply.status_code == 503


def test_route_planning_needs_a_login(api_client):
    reply = api_client.post(
        "/api/v1/routes/plan/", {"origin": [22.5, 88.3], "destination": [22.6, 88.4]}, format="json"
    )
    assert reply.status_code == 401
