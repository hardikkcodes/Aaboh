from __future__ import annotations

import io
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.core.geometry import point_geojson
from apps.locations.models import Area, AreaLevel, Neighbourhood
from apps.locations.services.grid import generate_grid

User = get_user_model()


@pytest.fixture(autouse=True)
def no_background_refresh(settings):
    settings.AUTO_REFRESH_DATA = False


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="resident",
        email="resident@example.com",
        password="a-very-long-password-123",
        display_name="Resident",
    )


@pytest.fixture
def moderator(db):
    return User.objects.create_user(
        username="moderator",
        email="moderator@example.com",
        password="a-very-long-password-123",
        display_name="Moderator",
        role="moderator",
    )


@pytest.fixture
def auth_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def moderator_client(moderator) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=moderator)
    return client


@pytest.fixture
def area(db) -> Area:
    """A small deterministic rectangular study area around central Kolkata."""
    boundary = {
        "type": "Polygon",
        "coordinates": [
            [
                [88.34, 22.54],
                [88.38, 22.54],
                [88.38, 22.58],
                [88.34, 22.58],
                [88.34, 22.54],
            ]
        ],
    }
    return Area.objects.create(
        slug="kolkata",
        name="Kolkata",
        level=AreaLevel.CITY,
        boundary=boundary,
        centroid=point_geojson(22.56, 88.36),
        centroid_lat=22.56,
        centroid_lon=88.36,
        area_km2=1,
    )


@pytest.fixture
def grid(area) -> Area:
    generate_grid(area, version="TEST-1KM-V1")
    return area


@pytest.fixture
def neighbourhood(area) -> Neighbourhood:
    return Neighbourhood.objects.create(
        area=area,
        slug="park-street",
        name="Park Street",
        point=point_geojson(22.553, 88.352),
        latitude=22.553,
        longitude=88.352,
    )


def make_image_bytes(size: tuple[int, int] = (320, 240), color=(60, 120, 90)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def image_upload() -> SimpleUploadedFile:
    return SimpleUploadedFile(
        "flood.png",
        make_image_bytes(),
        content_type="image/png",
    )


@pytest.fixture
def incident_payload(area, neighbourhood):
    return {
        "area": area.slug,
        "neighbourhood": neighbourhood.slug,
        "category": "waterlogging",
        "description": "Knee-deep water across the road near the crossing.",
        "occurred_at": (timezone.now() - timedelta(minutes=20)).isoformat(),
        "latitude": 22.553,
        "longitude": 88.352,
        "address_text": "Near the park crossing",
    }
