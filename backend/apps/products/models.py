import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.db import models

from .validators import validate_image_size


class WeightUnit(models.TextChoices):
    GRAM = "g", "گرم"
    KILOGRAM = "kg", "کیلوگرم"


def category_image_upload_path(instance, filename):
    return f"categories/{instance.id}/{filename}"


class Category(models.Model):
    """
    دسته‌بندی به‌صورت مستقل ساخته نمی‌شود؛ همیشه همراه اولین محصولش
    ساخته یا انتخاب می‌شود (نگاه کن به ProductWriteSerializer).
    عکس دسته‌بندی هم می‌تواند همان لحظه یا بعداً (از طریق
    CategoryDetailAPIView) تنظیم/تغییر داده شود.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    image = models.ImageField(
        upload_to=category_image_upload_path, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )

    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    price = models.DecimalField(max_digits=12, decimal_places=2)
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0")
    )  # 0 تا 100

    weight_value = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    weight_unit = models.CharField(
        max_length=5, choices=WeightUnit.choices, null=True, blank=True
    )

    raw_materials = models.JSONField(default=list, blank=True)   # ["سیب زمینی", "گوجه"]
    components = models.JSONField(default=list, blank=True)      # اگر پک بود، اجزای داخلش

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def final_price(self) -> Decimal:
        if self.discount_percent and self.discount_percent > 0:
            raw = self.price * (Decimal("100") - self.discount_percent) / Decimal("100")
            return raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return self.price


def product_image_upload_path(instance, filename):
    return f"products/{instance.product_id}/{filename}"


class ProductImage(models.Model):
    """
    فقط مسیر فایل در دیتابیس ذخیره می‌شود؛ فایل واقعی روی دیسک
    (MEDIA_ROOT/products/...) قرار می‌گیرد.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(
        upload_to=product_image_upload_path,
        validators=[validate_image_size],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]