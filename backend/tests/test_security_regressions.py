"""Regressions for rate limiting, report privacy and upload handling."""

from __future__ import annotations

import io
from datetime import timedelta
from unittest import mock

import pytest
from conftest import make_image_bytes
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image, ImageOps
from rest_framework.exceptions import ValidationError

from apps.core.geometry import point_geojson
from apps.incidents.models import IncidentReport
from apps.incidents.services import _clean_image

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_rate_limits():
    cache.clear()
    yield
    cache.clear()


def login_attempts(client, forwarded_for: list[str]) -> list[int]:
    return [
        client.post(
            "/api/v1/auth/login/",
            {"email": "nobody@example.com", "password": "wrong-password"},
            format="json",
            HTTP_X_FORWARDED_FOR=value,
        ).status_code
        for value in forwarded_for
    ]


def make_report(area, **overrides) -> IncidentReport:
    values = {
        "area": area,
        "category": "waterlogging",
        "description": "Water across the road near the crossing.",
        "occurred_at": timezone.now() - timedelta(hours=1),
        "point": point_geojson(22.553, 88.352),
        "latitude": 22.553,
        "longitude": 88.352,
    }
    return IncidentReport.objects.create(**{**values, **overrides})


def test_rotating_forwarded_for_does_not_escape_login_limit(api_client):
    statuses = login_attempts(api_client, [f"10.0.0.{index}" for index in range(12)])
    assert 429 in statuses


def test_behind_one_proxy_only_the_proxy_added_address_counts(api_client, settings):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}
    statuses = login_attempts(api_client, [f"10.0.0.{index}, 203.0.113.7" for index in range(12)])
    assert 429 in statuses


def test_moderator_note_is_hidden_from_the_public(area, api_client, moderator_client, user, auth_client):
    report = make_report(area, reporter=user)
    moderator_client.post(
        f"/api/v1/incidents/{report.id}/moderate/",
        {"status": "UNDER_REVIEW", "note": "private-note"},
        format="json",
    )

    assert "private-note" not in api_client.get(f"/api/v1/incidents/{report.id}/").content.decode()
    assert "private-note" not in api_client.get(f"/api/v1/incidents/{report.id}/history/").content.decode()
    assert "private-note" in auth_client.get(f"/api/v1/incidents/{report.id}/").content.decode()
    assert "private-note" in moderator_client.get(f"/api/v1/incidents/{report.id}/history/").content.decode()


def test_duplicate_hints_respect_visibility(area, api_client, moderator_client):
    public = make_report(area)
    hidden = make_report(area, is_public=False, status="VERIFIED")

    assert api_client.get(f"/api/v1/incidents/{public.id}/").json()["potential_duplicates"] == []
    hints = moderator_client.get(f"/api/v1/incidents/{public.id}/").json()["potential_duplicates"]
    assert [hint["id"] for hint in hints] == [str(hidden.id)]


def test_insights_exclude_hidden_reports(area, api_client):
    verified = make_report(area, is_public=False, status="VERIFIED", verified_at=timezone.now())
    unverified = make_report(area, is_public=False)

    body = api_client.get("/api/v1/insights/?area=kolkata").content.decode()

    assert str(verified.id) not in body
    assert str(unverified.id) not in body


@pytest.mark.parametrize(
    "address",
    ["12 Lake View Road", "flat 4B near the park", "call 98300 12345", "me@example.com"],
)
def test_precise_addresses_are_rejected_on_create_and_edit(
    area, neighbourhood, auth_client, user, incident_payload, address
):
    created = auth_client.post("/api/v1/incidents/", {**incident_payload, "address_text": address}, format="json")
    assert created.status_code == 400

    report = make_report(area, reporter=user)
    edited = auth_client.patch(f"/api/v1/incidents/{report.id}/", {"address_text": address}, format="json")
    assert edited.status_code == 400


def test_landmarks_with_numbers_are_allowed(area, neighbourhood, auth_client, incident_payload):
    response = auth_client.post(
        "/api/v1/incidents/", {**incident_payload, "address_text": "Near Gate 3, Sector 5"}, format="json"
    )
    assert response.status_code == 201


def test_oversized_image_is_rejected_before_decoding():
    buffer = io.BytesIO()
    Image.new("RGB", (7000, 7000), (1, 2, 3)).save(buffer, "PNG", compress_level=1)
    upload = SimpleUploadedFile("large.png", buffer.getvalue(), content_type="image/png")

    with mock.patch.object(ImageOps, "exif_transpose") as decode, pytest.raises(ValidationError):
        _clean_image(upload)

    decode.assert_not_called()


def test_failed_multi_image_upload_leaves_no_files(settings, tmp_path, area, neighbourhood, auth_client, incident_payload):
    settings.MEDIA_ROOT = tmp_path
    good = SimpleUploadedFile("good.png", make_image_bytes(), content_type="image/png")
    tiny = SimpleUploadedFile("tiny.png", make_image_bytes((50, 50)), content_type="image/png")

    response = auth_client.post(
        "/api/v1/incidents/", {**incident_payload, "attachments": [good, tiny]}, format="multipart"
    )

    assert response.status_code == 400
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]


def test_model_info_does_not_expose_server_paths(api_client):
    from apps.heat.serializers import ModelVersionSerializer

    assert "artifact_path" not in ModelVersionSerializer.Meta.fields
