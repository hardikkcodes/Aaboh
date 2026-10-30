from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsModerator(BasePermission):
    message = "Only authorized moderators may perform this action."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "is_moderator", False))


class IsOwnerOrModerator(BasePermission):
    """Object-level permission for user-owned resources."""

    def has_object_permission(self, request, view, obj) -> bool:
        if request.method in SAFE_METHODS:
            return True
        if getattr(request.user, "is_moderator", False):
            return True
        owner = getattr(obj, "user", None) or getattr(obj, "reporter", None)
        return bool(owner and owner == request.user)
