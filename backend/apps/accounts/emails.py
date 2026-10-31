"""Account emails. A failed send is logged and never breaks the request that caused it."""

from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

logger = logging.getLogger(__name__)
User = get_user_model()

VERIFY_SALT = "accounts.verify-email"
VERIFY_MAX_AGE_SECONDS = 3 * 24 * 60 * 60


def _frontend(path: str) -> str:
    return f"{settings.APP_CONFIG['frontend_url'].rstrip('/')}{path}"


def _send(user, subject: str, body: str) -> None:
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception:  # noqa: BLE001 - the mail host must not decide whether an account works
        logger.exception("Could not send account email")


def send_verification_email(user) -> None:
    token = signing.dumps({"user": str(user.pk), "email": user.email}, salt=VERIFY_SALT)
    link = _frontend(f"/verify-email?token={token}")
    _send(
        user,
        f"Confirm your {settings.APP_CONFIG['name']} email",
        f"Open this link to confirm your email address:\n\n{link}\n\nIt works for 3 days.",
    )


def verify_email_token(token: str):
    """The user the token belongs to, or None. A changed email invalidates old links."""
    try:
        payload = signing.loads(token, salt=VERIFY_SALT, max_age=VERIFY_MAX_AGE_SECONDS)
    except signing.BadSignature:
        return None
    return User.objects.filter(pk=payload["user"], email=payload["email"], is_active=True).first()


def send_password_reset_email(user) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = _frontend(f"/reset-password?uid={uid}&token={token}")
    _send(
        user,
        f"Reset your {settings.APP_CONFIG['name']} password",
        f"Open this link to choose a new password:\n\n{link}\n\n"
        "If you didn't ask for this, you can ignore this email.",
    )


def user_for_reset(uid: str, token: str):
    try:
        user = User.objects.filter(pk=force_str(urlsafe_base64_decode(uid)), is_active=True).first()
    except (TypeError, ValueError, OverflowError, UnicodeDecodeError):
        return None
    except Exception:  # noqa: BLE001 - a malformed uid is not a valid UUID
        return None
    return user if user and default_token_generator.check_token(user, token) else None
