# همون IsAdmin که برای users/products ساخته شده را دوباره‌نویسی نمی‌کنیم؛ فقط ایمپورت می‌کنیم
from apps.users.permissions import IsAdmin  # noqa: F401
