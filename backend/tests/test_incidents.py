from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.incidents.models import IncidentAttachment, IncidentReport, IncidentStatus


@pytest.mark.django_db
def test_report_submission_requires_authentication(api_client, incident_payload):
    response = api_client.post("/api/v1/incidents/", incident_payload, format="json")
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_report_submission_stores_unverified_report_and_sanitises_image(
    auth_client, incident_payload, image_upload
):
    response = auth_client.post(
        "/api/v1/incidents/",
        {**incident_payload, "attachments": [image_upload]},
        format="multipart",
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["status"] == IncidentStatus.SUBMITTED
    assert body["verification_state"] == "UNVERIFIED"
    assert body["is_owner"] is True
    assert len(body["attachments"]) == 1

    attachment = IncidentAttachment.objects.get()
    assert attachment.content_type == "image/jpeg"
    assert attachment.file.name.endswith(".jpg")
    assert attachment.size_bytes > 0
    assert len(attachment.sha256) == 64

    # The public detail must not expose reporter identity.
    public_response = auth_client.get(f"/api/v1/incidents/{body['id']}/")
    assert public_response.status_code == 200
    assert "reporter" not in public_response.json()


@pytest.mark.django_db
def test_report_rejects_non_image_attachment(auth_client, incident_payload):
    upload = SimpleUploadedFile("notes.txt", b"not an image", content_type="text/plain")
    response = auth_client.post(
        "/api/v1/incidents/",
        {**incident_payload, "attachments": [upload]},
        format="multipart",
    )
    assert response.status_code == 400
    assert "attachments" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_report_rejects_corrupt_image_claiming_to_be_png(auth_client, incident_payload):
    upload = SimpleUploadedFile("broken.png", b"\x89PNG\r\n\x1a\nnot-really", content_type="image/png")
    response = auth_client.post(
        "/api/v1/incidents/",
        {**incident_payload, "attachments": [upload]},
        format="multipart",
    )
    assert response.status_code == 400
    assert "attachments" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_report_rejects_oversized_image(auth_client, incident_payload, settings):
    settings.INCIDENT_IMAGE_MAX_BYTES = 256
    upload = SimpleUploadedFile(
        "large.png",
        b"\x89PNG\r\n\x1a\n" + b"0" * 1024,
        content_type="image/png",
    )
    response = auth_client.post(
        "/api/v1/incidents/",
        {**incident_payload, "attachments": [upload]},
        format="multipart",
    )
    assert response.status_code == 400
    assert "attachments" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_report_rejects_too_many_attachments(auth_client, incident_payload, image_upload, settings):
    settings.INCIDENT_IMAGE_MAX_COUNT = 1
    second = SimpleUploadedFile(
        "second.png",
        image_upload.read(),
        content_type="image/png",
    )
    response = auth_client.post(
        "/api/v1/incidents/",
        {**incident_payload, "attachments": [image_upload, second]},
        format="multipart",
    )
    assert response.status_code == 400
    assert "attachments" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_report_outside_area_is_rejected(auth_client, incident_payload):
    payload = {**incident_payload, "latitude": 23.5, "longitude": 88.36}
    response = auth_client.post("/api/v1/incidents/", payload, format="json")
    assert response.status_code == 400
    assert "latitude" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_report_description_and_time_validation(auth_client, incident_payload):
    short = {**incident_payload, "description": "wet"}
    response = auth_client.post("/api/v1/incidents/", short, format="json")
    assert response.status_code == 400

    future = {**incident_payload, "occurred_at": (timezone.now() + timedelta(hours=2)).isoformat()}
    response = auth_client.post("/api/v1/incidents/", future, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_moderation_requires_moderator_and_records_history(auth_client, moderator_client, incident_payload):
    created = auth_client.post("/api/v1/incidents/", incident_payload, format="json").json()
    url = f"/api/v1/incidents/{created['id']}/moderate/"

    forbidden = auth_client.post(url, {"status": "VERIFIED"}, format="json")
    assert forbidden.status_code == 403

    verified = moderator_client.post(url, {"status": "VERIFIED", "note": "Checked with photo"}, format="json")
    assert verified.status_code == 200
    assert verified.json()["status"] == IncidentStatus.VERIFIED
    assert verified.json()["verification_state"] == "VERIFIED"

    resolved = moderator_client.post(
        f"/api/v1/incidents/{created['id']}/moderate/",
        {"status": "RESOLVED", "note": "Water cleared"},
        format="json",
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == IncidentStatus.RESOLVED
    assert resolved.json()["resolved_at"] is not None

    history = moderator_client.get(f"/api/v1/incidents/{created['id']}/history/").json()
    assert history["count"] == 3
    assert history["results"][-1]["to_status"] == IncidentStatus.RESOLVED


@pytest.mark.django_db
def test_invalid_status_transition_is_rejected(moderator_client, auth_client, incident_payload):
    created = auth_client.post("/api/v1/incidents/", incident_payload, format="json").json()
    response = moderator_client.post(
        f"/api/v1/incidents/{created['id']}/moderate/",
        {"status": "RESOLVED"},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_duplicate_marking_requires_original(moderator_client, auth_client, incident_payload):
    created = auth_client.post("/api/v1/incidents/", incident_payload, format="json").json()
    response = moderator_client.post(
        f"/api/v1/incidents/{created['id']}/moderate/",
        {"status": "DUPLICATE"},
        format="json",
    )
    assert response.status_code == 400
    assert "duplicate_of" in response.json()["error"]["details"]


@pytest.mark.django_db
def test_nearby_report_returns_duplicate_hint(auth_client, incident_payload):
    first = auth_client.post("/api/v1/incidents/", incident_payload, format="json")
    assert first.status_code == 201

    second_payload = {
        **incident_payload,
        "latitude": 22.5533,
        "longitude": 88.3522,
        "description": "Water is still standing at the same junction after an hour.",
    }
    second = auth_client.post("/api/v1/incidents/", second_payload, format="json")
    assert second.status_code == 201
    hints = second.json()["potential_duplicates"]
    assert len(hints) == 1
    assert hints[0]["id"] == first.json()["id"]
    assert hints[0]["verification_state"] == "UNVERIFIED"
    assert IncidentReport.objects.count() == 2


@pytest.mark.django_db
def test_rejected_report_is_hidden_from_public_list(moderator_client, api_client, auth_client, incident_payload):
    created = auth_client.post("/api/v1/incidents/", incident_payload, format="json").json()
    moderator_client.post(
        f"/api/v1/incidents/{created['id']}/moderate/",
        {"status": "REJECTED", "note": "Not reproducible"},
        format="json",
    )
    public = api_client.get("/api/v1/incidents/")
    assert public.status_code == 200
    assert public.json()["count"] == 0


@pytest.mark.django_db
def test_owner_can_edit_until_verified(auth_client, moderator_client, incident_payload):
    created = auth_client.post("/api/v1/incidents/", incident_payload, format="json").json()
    edited = auth_client.patch(
        f"/api/v1/incidents/{created['id']}/",
        {"description": "Water has receded but the drain is still blocked."},
        format="json",
    )
    assert edited.status_code == 200

    moderator_client.post(
        f"/api/v1/incidents/{created['id']}/moderate/",
        {"status": "VERIFIED"},
        format="json",
    )
    locked = auth_client.patch(
        f"/api/v1/incidents/{created['id']}/",
        {"description": "Trying to edit after verification."},
        format="json",
    )
    assert locked.status_code == 400


@pytest.mark.django_db
def test_summary_counts_reports(auth_client, incident_payload):
    auth_client.post("/api/v1/incidents/", incident_payload, format="json")
    response = auth_client.get("/api/v1/incidents/summary/")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["unverified"] == 1
    assert body["verified"] == 0
    assert body["by_category"]["waterlogging"] == 1
