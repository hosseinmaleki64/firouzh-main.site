from rest_framework.permissions import BasePermission
from apps.authentication.models import UserRole


class IsAdmin(BasePermission):
    """
    فقط ADMIN و SUPER_ADMIN
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in [
                UserRole.ADMIN,
                UserRole.SUPER_ADMIN,
            ]
        )


class IsSuperAdmin(BasePermission):
    """
    فقط SUPER_ADMIN
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == UserRole.SUPER_ADMIN
        )