import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.products.models import Product

CART_EXPIRY_DAYS = 7


class CartStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "فعال"
    ORDERED = "ORDERED", "تبدیل به سفارش شده"
    ABANDONED = "ABANDONED", "رهاشده"


class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # اگر کاربر لاگین کرده باشد پر می‌شود
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="carts",
    )
    # اگر مهمان باشد پر می‌شود
    session_key = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    status = models.CharField(
        max_length=12, choices=CartStatus.choices, default=CartStatus.ACTIVE
    )
    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["session_key", "status"]),
        ]

    def __str__(self):
        return f"Cart({self.user or self.session_key})"

    def touch(self):
        self.expires_at = timezone.now() + timedelta(days=CART_EXPIRY_DAYS)
        self.save(update_fields=["expires_at", "updated_at"])


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)  # snapshot لحظه‌ی افزودن

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="unique_product_per_cart")
        ]

    @property
    def total_price(self):
        return self.unit_price * self.quantity