from django.conf import settings
from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsModerator(BasePermission):
    message = "Only authorized moderators may perform this action."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_moderator", False))


class VerifiedEmailToWrite(BasePermission):
    """Once delivery works, operators can require a confirmed email before reporting."""

    message = "Confirm your email address before reporting."

    def has_permission(self, request, view) -> bool:
        if request.method in SAFE_METHODS or not settings.ACCOUNT_REQUIRE_VERIFIED_EMAIL:
            return True
        return bool(getattr(request.user, "email_verified", False))


class IsOwnerOrModerator(BasePermission):
    """Object-level permission for user-owned resources."""

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        if getattr(request.user, "is_moderator", False):
            return True
        owner = getattr(obj, "user", None) or getattr(obj, "reporter", None)
        return bool(owner and owner == request.user)
