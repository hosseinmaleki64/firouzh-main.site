from rest_framework.permissions import SAFE_METHODS, BasePermission
from apps.authentication.models import UserRole


class IsAdminOrReadOnly(BasePermission):
    """
    هرکسی اجازه‌ی خواندن (GET/HEAD/OPTIONS) دارد.
    فقط ADMIN و SUPER_ADMIN اجازه‌ی ساخت/ویرایش/حذف دارند.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)
        )


class IsContentManager(BasePermission):
    """
    فقط ADMIN و SUPER_ADMIN - برای اکشن‌های مدیریتی
    (publish / draft / archive) که نباید حتی GET عمومی داشته باشند.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)
        )