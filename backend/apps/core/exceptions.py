"""Consistent API error envelope.

Every error response has the shape::

    {"error": {"code": "...", "message": "...", "details": ...}}

``details`` is a field-error map for validation failures and ``null`` otherwise.
"""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("apps.api.errors")

_STATUS_CODES = {
    status.HTTP_400_BAD_REQUEST: "validation_error",
    status.HTTP_401_UNAUTHORIZED: "not_authenticated",
    status.HTTP_403_FORBIDDEN: "permission_denied",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_429_TOO_MANY_REQUESTS: "throttled",
}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled API exception", exc_info=exc)
        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected server error occurred.",
                    "details": None,
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    code = getattr(exc, "default_code", None) or _STATUS_CODES.get(response.status_code, "error")
    if isinstance(exc, ValidationError):
        code = _STATUS_CODES[status.HTTP_400_BAD_REQUEST]
    details = None
    message = "Request could not be completed."

    if isinstance(exc, ValidationError):
        message = "Validation failed."
        details = response.data
    elif isinstance(response.data, dict) and "detail" in response.data:
        message = str(response.data["detail"])
    elif isinstance(response.data, (dict, list)):
        details = response.data
    else:
        message = str(response.data)

    if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        message = str(getattr(exc, "detail", "Request rate limit exceeded."))

    # Preserve domain-specific error codes declared on custom exceptions.
    if isinstance(exc, APIException) and getattr(exc, "error_code", None):
        code = exc.error_code  # type: ignore[attr-defined]

    response.data = {"error": {"code": code, "message": message, "details": details}}
    return response
