import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.products.models import Product
from apps.authentication.utils import normalize_phone
# توجه: به‌جای ایمپورت مستقیم Cart، از رفرنس رشته‌ای "cart.Cart" در FK استفاده می‌شود
# تا وابستگی مستقیم/چرخه‌ای بین اپ orders و cart ایجاد نشود.


# =========================================================
# انتخاب‌ها (Choices)
# =========================================================

class OrderStatus(models.TextChoices):
    PENDING_PAYMENT = "PENDING_PAYMENT", "در انتظار پرداخت"
    PAID = "PAID", "پرداخت موفق"
    CONFIRMED = "CONFIRMED", "تایید شده"
    PREPARING = "PREPARING", "در حال آماده‌سازی"
    READY = "READY", "آماده ارسال"
    SHIPPED = "SHIPPED", "ارسال شده"
    DELIVERED = "DELIVERED", "تحویل شده"
    CANCELLED = "CANCELLED", "لغو شده"


# مسیر خطی/شادِ تایم‌لاین (برای دکمه‌ی «مرحله‌ی بعد»)
STATUS_FLOW = [
    OrderStatus.PENDING_PAYMENT,
    OrderStatus.PAID,
    OrderStatus.CONFIRMED,
    OrderStatus.PREPARING,
    OrderStatus.READY,
    OrderStatus.SHIPPED,
    OrderStatus.DELIVERED,
]

# انتقال‌های مجاز از هر وضعیت (شامل مسیر لغو)
ALLOWED_TRANSITIONS = {
    OrderStatus.PENDING_PAYMENT: [OrderStatus.PAID, OrderStatus.CANCELLED],
    OrderStatus.PAID: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
    OrderStatus.PREPARING: [OrderStatus.READY, OrderStatus.CANCELLED],
    OrderStatus.READY: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
    OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: [],
}


class ShippingMethod(models.TextChoices):
    COURIER = "COURIER", "پیک"
    POST = "POST", "پست"
    PICKUP = "PICKUP", "تحویل حضوری"


class PaymentMethod(models.TextChoices):
    CASH_ON_DELIVERY = "COD", "پرداخت در محل"
    ONLINE_GATEWAY = "ONLINE", "درگاه آنلاین"
    CARD_TO_CARD = "CARD", "کارت به کارت"


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "در انتظار پرداخت"
    SUCCESS = "SUCCESS", "موفق"
    FAILED = "FAILED", "ناموفق"
    REFUNDED = "REFUNDED", "بازگشت وجه"


# =========================================================
# مشتری
# =========================================================

class Customer(models.Model):
    """
    مشتری مستقل از حساب کاربری (User) نگه‌داری می‌شود تا سفارش‌های مهمان
    (بدون لاگین) هم بتوانند بر اساس شماره تلفن، سابقه و پروفایل داشته باشند.
    اگر کاربر بعداً ثبت‌نام/لاگین کند، همین رکورد به user متصل می‌شود.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="customer_profile",
    )

    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=13, unique=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.phone})"

    def save(self, *args, **kwargs):
        if self.phone:
            self.phone = normalize_phone(self.phone)
        super().save(*args, **kwargs)


class Address(models.Model):
    """
    دفترچه آدرس‌های یک مشتری (برای استفاده مجدد در سفارش‌های بعدی).
    توجه: سفارش، آدرس را به‌صورت اسنپ‌شات (کپی) نگه می‌دارد نه رفرنس زنده،
    چون اگر مشتری بعداً این آدرس را ویرایش/حذف کند نباید سفارش‌های قبلی تغییر کنند.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="addresses")

    title = models.CharField(max_length=50, blank=True)  # مثلاً "خانه"، "محل کار"
    full_address = models.TextField()
    postal_code = models.CharField(max_length=10, blank=True)
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.title or 'آدرس'} - {self.customer.full_name}"


# =========================================================
# کد تخفیف
# =========================================================

class DiscountType(models.TextChoices):
    PERCENT = "PERCENT", "درصدی"
    FIXED = "FIXED", "مبلغ ثابت"


class Coupon(models.Model):
    """
    کد تخفیف واقعی که سمت بک‌اند اعتبارسنجی می‌شود.
    قبلاً این منطق هاردکد و سمت جاوااسکریپت بود (قابل مشاهده و دستکاری در سورس)؛
    از این به بعد فقط یک رشته‌ی بی‌معنی است تا سرور تاییدش کند.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True, db_index=True)

    discount_type = models.CharField(max_length=10, choices=DiscountType.choices, default=DiscountType.PERCENT)
    value = models.DecimalField(max_digits=10, decimal_places=2)  # درصد (۰-۱۰۰) یا مبلغ ثابت به تومان

    min_order_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    max_discount_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="سقف تخفیف برای نوع درصدی (اختیاری)",
    )

    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    usage_limit = models.PositiveIntegerField(null=True, blank=True, help_text="خالی = بدون محدودیت")
    used_count = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    def is_valid_now(self) -> bool:
        if not self.is_active:
            return False
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False
        return True

    def calculate_discount(self, subtotal: Decimal) -> Decimal:
        if subtotal < self.min_order_amount:
            return Decimal("0")
        if self.discount_type == DiscountType.FIXED:
            amount = self.value
        else:
            amount = (subtotal * self.value / Decimal("100")).quantize(Decimal("1"))
        if self.max_discount_amount is not None:
            amount = min(amount, self.max_discount_amount)
        return min(amount, subtotal)


# =========================================================
# سفارش
# =========================================================

def generate_order_number() -> str:
    """
    شماره سفارش ترتیبی و انسانی تولید می‌کند (مثل #1028).
    با select_for_update روی ردیف شمارنده، از race condition جلوگیری می‌شود.
    """
    with transaction.atomic():
        counter, _ = OrderCounter.objects.select_for_update().get_or_create(
            id=1, defaults={"last_number": 1000}
        )
        counter.last_number += 1
        counter.save(update_fields=["last_number"])
        return str(counter.last_number)


class OrderCounter(models.Model):
    """
    یک ردیف تکی (singleton) برای تولید شماره سفارش ترتیبی.
    """
    id = models.SmallAutoField(primary_key=True)
    last_number = models.PositiveIntegerField(default=1000)


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=20, unique=True, editable=False, db_index=True)

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")

    # اسنپ‌شات آدرس تحویل (مستقل از دفترچه آدرس، برای ثبات تاریخی)
    shipping_recipient_name = models.CharField(max_length=100)
    shipping_recipient_phone = models.CharField(max_length=13)
    shipping_full_address = models.TextField()
    shipping_postal_code = models.CharField(max_length=10, blank=True)
    source_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )

    # لینک اختیاری به سبد خریدی که سفارش از آن ساخته شده (برای ردیابی/آمار)
    source_cart = models.ForeignKey(
        "cart.Cart", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )

    # اطلاعات سفارش
    event_time = models.DateTimeField(null=True, blank=True)  # زمان مراسم
    delivery_window = models.CharField(max_length=100, blank=True)  # بازه تحویل، مثلاً "16:00-18:00"
    shipping_method = models.CharField(
        max_length=10, choices=ShippingMethod.choices, default=ShippingMethod.COURIER
    )
    table_arrangement = models.CharField(max_length=255, blank=True)  # میزآرایی

    status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING_PAYMENT
    )

    customer_note = models.TextField(blank=True)  # یادداشت مشتری - به مشتری هم نمایش داده می‌شود
    admin_note = models.TextField(blank=True)  # یادداشت مدیر - فقط داخلی، هرگز به مشتری نشان داده نمی‌شود

    # خلاصه مالی (اسنپ‌شات لحظه ثبت سفارش)
    items_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["order_number"]),
        ]

    def __str__(self):
        return f"#{self.order_number}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = generate_order_number()
        super().save(*args, **kwargs)

    @property
    def items_count(self):
        # از prefetch استفاده می‌کند اگر انجام شده باشد
        return sum(item.quantity for item in self.items.all())

    @property
    def is_event_today(self) -> bool:
        if not self.event_time:
            return False
        return self.event_time.date() == timezone.localdate()

    @property
    def is_delivery_urgent(self) -> bool:
        """
        اگر کمتر از دو ساعت تا زمان مراسم مانده باشد True برمی‌گرداند
        (برای نمایش اول لیست / بج هشدار در فرانت).
        """
        if not self.event_time:
            return False
        now = timezone.now()
        return now <= self.event_time <= now + timezone.timedelta(hours=2)


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")

    # اسنپ‌شات لحظه سفارش (اگر بعداً اسم/قیمت محصول عوض شد، فاکتور قدیمی درست بماند)
    product_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"

    @property
    def total_price(self):
        return self.unit_price * self.quantity


# =========================================================
# پرداخت و فاکتور
# =========================================================

class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")

    method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH_ON_DELIVERY)
    status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    # شناسه‌ای که درگاه (زرین‌پال) قبل از پرداخت برمی‌گرداند؛ برای verify بعد از بازگشت کاربر لازم است
    gateway_authority = models.CharField(max_length=64, blank=True, db_index=True)
    # کد پیگیری نهایی که بعد از verify موفق از درگاه دریافت می‌شود
    transaction_id = models.CharField(max_length=100, blank=True)
    is_sandbox = models.BooleanField(default=False)

    gateway_response = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment({self.order.order_number})"


class Invoice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")

    invoice_number = models.CharField(max_length=30, unique=True, editable=False)
    pdf_file = models.FileField(upload_to="invoices/", null=True, blank=True)

    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.invoice_number

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = f"INV-{self.order.order_number}"
        super().save(*args, **kwargs)


# =========================================================
# تاریخچه وضعیت
# =========================================================

class OrderStatusHistory(models.Model):
    """
    هر تغییر وضعیت سفارش، یک رکورد جدا اینجا ثبت می‌شود (نه فقط overwrite فیلد status).
    این باعث می‌شود تایم‌لاین کامل سفارش (چه زمانی، توسط چه کسی) همیشه در دسترس باشد.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")

    status = models.CharField(max_length=20, choices=OrderStatus.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="order_status_changes",
    )
    note = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.order.order_number} -> {self.status}"
