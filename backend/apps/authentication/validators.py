import re

from django.core.exceptions import ValidationError


def validate_iranian_phone(phone: str):
    """
    انتظار دارد phone از قبل نرمال شده باشد (خروجی normalize_phone)،
    یعنی فرمت +989XXXXXXXXX.

    ValidationError پرتاب می‌کند (نه ValueError) تا هم به‌عنوان
    validator فیلد مدل قابل استفاده باشد و هم پیام آن یکدست با
    بقیه‌ی خطاهای جنگو/DRF نمایش داده شود.
    """
    pattern = r"^\+989\d{9}$"

    if not re.match(pattern, phone):
        raise ValidationError("شماره موبایل معتبر نیست.")
