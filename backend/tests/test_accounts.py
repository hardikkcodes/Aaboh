from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import SavedLocation

pytestmark = pytest.mark.django_db


def test_register_creates_account_and_token(api_client):
    response = api_client.post(
        reverse("accounts:register"),
        {
            "email": "New.Resident@Example.com",
            "password": "another-long-password-456",
            "display_name": "New Resident",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["token"]
    assert response.data["user"]["email"] == "new.resident@example.com"
    assert response.data["user"]["display_name"] == "New Resident"


def test_register_rejects_duplicate_email(api_client, user):
    response = api_client.post(
        reverse("accounts:register"),
        {"email": user.email, "password": "another-long-password-456"},
        format="json",
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"
    assert "email" in response.data["error"]["details"]


def test_register_rejects_weak_password(api_client):
    response = api_client.post(
        reverse("accounts:register"),
        {"email": "weak@example.com", "password": "123"},
        format="json",
    )
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"


def test_login_returns_token(api_client, user):
    response = api_client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": "a-very-long-password-123"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["token"]
    assert response.data["user"]["id"] == str(user.id)


def test_login_rejects_bad_password_without_leaking_account(api_client, user):
    response = api_client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": "wrong-password-123"},
        format="json",
    )
    assert response.status_code == 400
    assert "Invalid email or password" in str(response.data)


def test_token_authentication_reaches_me_endpoint(api_client, user):
    login = api_client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": "a-very-long-password-123"},
        format="json",
    )
    token = login.data["token"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    response = api_client.get(reverse("accounts:me"))
    assert response.status_code == 200
    assert response.data["email"] == user.email
    assert "preferences" in response.data


def test_me_requires_authentication(api_client):
    response = api_client.get(reverse("accounts:me"))
    assert response.status_code in {401, 403}
    assert response.data["error"]["code"] in {"not_authenticated", "permission_denied"}


def test_logout_revokes_token(auth_client, api_client, user):
    login = api_client.post(
        reverse("accounts:login"),
        {"email": user.email, "password": "a-very-long-password-123"},
        format="json",
    )
    token = login.data["token"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    assert api_client.post(reverse("accounts:logout")).status_code == 204
    assert api_client.get(reverse("accounts:me")).status_code in {401, 403}


def test_profile_update_validates_display_name(auth_client):
    ok = auth_client.patch(
        reverse("accounts:me"), {"display_name": "  Renamed  "}, format="json"
    )
    assert ok.status_code == 200
    assert ok.data["display_name"] == "Renamed"

    bad = auth_client.patch(reverse("accounts:me"), {"display_name": "   "}, format="json")
    assert bad.status_code == 400


def test_preferences_update_unit_and_area(auth_client, area):
    response = auth_client.patch(
        reverse("accounts:preferences"),
        {"temperature_unit": "F", "default_area": area.slug},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["preferences"]["temperature_unit"] == "F"
    assert response.data["preferences"]["default_area"] == area.slug


def test_preferences_reject_unknown_unit(auth_client):
    response = auth_client.patch(
        reverse("accounts:preferences"), {"temperature_unit": "K"}, format="json"
    )
    assert response.status_code == 400


def test_saved_locations_enforce_area_boundary(auth_client, area):
    inside = auth_client.post(
        reverse("accounts:saved-locations"),
        {
            "label": "Park Street",
            "area": area.slug,
            "latitude": 22.553,
            "longitude": 88.352,
        },
        format="json",
    )
    assert inside.status_code == 201
    assert inside.data["point"]["type"] == "Point"

    outside = auth_client.post(
        reverse("accounts:saved-locations"),
        {
            "label": "Far away",
            "area": area.slug,
            "latitude": 22.7,
            "longitude": 88.5,
        },
        format="json",
    )
    assert outside.status_code == 400


def test_saved_location_delete_is_scoped_to_owner(auth_client, moderator_client, area):
    created = auth_client.post(
        reverse("accounts:saved-locations"),
        {"label": "Home", "area": area.slug, "latitude": 22.55, "longitude": 88.35},
        format="json",
    )
    assert created.status_code == 201
    pk = created.data["id"]
    assert SavedLocation.objects.filter(pk=pk).exists()

    denied = moderator_client.delete(reverse("accounts:saved-location-detail", args=[pk]))
    assert denied.status_code == 404

    removed = auth_client.delete(reverse("accounts:saved-location-detail", args=[pk]))
    assert removed.status_code == 204
    assert not SavedLocation.objects.filter(pk=pk).exists()


def test_saved_locations_require_authentication(api_client):
    assert api_client.get(reverse("accounts:saved-locations")).status_code in {401, 403}


def test_openapi_schema_is_generated(api_client):
    response = api_client.get(reverse("schema"), HTTP_ACCEPT="application/vnd.oai.openapi+json")
    assert response.status_code == 200
    document = response.json()
    assert document["openapi"].startswith("3.")
    assert "/api/v1/weather/current/" in document["paths"]
    assert "/api/v1/incidents/" in document["paths"]
    # Detail operation IDs are explicitly disambiguated.
    assert document["paths"]["/api/v1/alerts/{id}/"]["get"]["operationId"] == "alerts_detail"
