"""Shared OpenAPI documentation helpers.

Most public endpoints return composed payloads rather than a single DRF
serializer. ``DocumentedAPIView`` documents those responses as free-form objects
instead of emitting drf-spectacular "unable to guess serializer" warnings while
keeping the endpoint visible in the schema.
"""

from __future__ import annotations

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView


@extend_schema(responses={200: OpenApiTypes.OBJECT})
class DocumentedAPIView(APIView):
    """APIView whose response schema is explicitly documented as a JSON object."""
