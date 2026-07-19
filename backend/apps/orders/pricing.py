"""
محاسبه‌ی قیمت‌ها فقط و فقط اینجا (سمت سرور) انجام می‌شود.
فرانت می‌تواند همین منطق را برای پیش‌نمایش UI کپی کند، اما منبع واقعی و نهایی همیشه این فایل است؛
مقادیر پولی هرگز نباید مستقیماً از body درخواست کاربر خوانده شوند.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

BASE_SHIPPING_COST = Decimal("30000")
NIGHT_SURCHARGE = Decimal("20000")      # تحویل بین ساعت ۲۱ تا ۸ صبح
WEEKEND_SURCHARGE = Decimal("15000")    # تحویل پنجشنبه/جمعه
TAX_RATE = Decimal("0.09")
MIN_DELIVERY_DAYS_AHEAD = 3


def calculate_shipping_cost(event_time) -> Decimal:
    """
    event_time: datetime آگاه از timezone (زمان مراسم/تحویل).
    همون منطقی که قبلاً در calculateDeliveryFee جاوااسکریپت بود، اینجا تکرار شده.
    """
    if event_time is None:
        return BASE_SHIPPING_COST

    cost = BASE_SHIPPING_COST
    local_time = timezone.localtime(event_time)

    hour = local_time.hour
    if hour >= 21 or hour < 8:
        cost += NIGHT_SURCHARGE

    # weekday() پایتون: دوشنبه=0 ... بنابراین پنجشنبه=3 و جمعه=4
    if local_time.weekday() in (3, 4):
        cost += WEEKEND_SURCHARGE

    return cost


def calculate_tax(items_total: Decimal, rate: Decimal = TAX_RATE) -> Decimal:
    return (items_total * rate).quantize(Decimal("1"))


def validate_delivery_time(event_time) -> None:
    if event_time is None:
        raise ValidationError("زمان تحویل الزامی است.")
    now = timezone.now()
    min_allowed = now + timezone.timedelta(days=MIN_DELIVERY_DAYS_AHEAD)
    # فقط تاریخ (نه ساعت دقیق) مثل نسخه‌ی فرانت مقایسه می‌شود
    if event_time.date() < min_allowed.date():
        raise ValidationError(
            f"زمان تحویل باید حداقل {MIN_DELIVERY_DAYS_AHEAD} روز آینده باشد."
        )


def apply_coupon(code: str, subtotal: Decimal):
    """
    کد تخفیف را اعتبارسنجی و مبلغ تخفیف را برمی‌گرداند.
    خروجی: (discount_amount: Decimal, coupon: Coupon | None)
    """
    from .models import Coupon  # جلوگیری از import چرخه‌ای

    if not code:
        return Decimal("0"), None

    try:
        coupon = Coupon.objects.get(code__iexact=code.strip())
    except Coupon.DoesNotExist:
        raise ValidationError("کد تخفیف نامعتبر است.")

    if not coupon.is_valid_now():
        raise ValidationError("این کد تخفیف منقضی شده یا غیرفعال است.")

    discount = coupon.calculate_discount(subtotal)
    if discount <= 0:
        raise ValidationError("این کد تخفیف برای این مبلغ سفارش قابل استفاده نیست.")

    return discount, coupon
