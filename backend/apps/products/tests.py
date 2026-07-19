import io
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import Category, Product, ProductImage
from .serializers import BulkPriceUpdateSerializer
from .validators import MAX_IMAGE_SIZE_BYTES, MAX_IMAGES_PER_PRODUCT


def make_image_file(name="test.png", size_bytes=1024):
    """یک فایل تصویری معتبر و کوچک برای تست می‌سازد (PNG یک‌پیکسلی + padding)."""
    png_1x1 = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
        b"\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    padding = b"0" * max(0, size_bytes - len(png_1x1))
    return SimpleUploadedFile(name, png_1x1 + padding, content_type="image/png")


class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="نوشیدنی")

    def test_final_price_without_discount(self):
        product = Product.objects.create(
            category=self.category, name="آب معدنی", price=Decimal("100.00")
        )
        self.assertEqual(product.final_price, Decimal("100.00"))

    def test_final_price_with_discount(self):
        product = Product.objects.create(
            category=self.category,
            name="نوشابه",
            price=Decimal("100.00"),
            discount_percent=Decimal("10.00"),
        )
        self.assertEqual(product.final_price, Decimal("90.00"))

    def test_product_image_rejects_oversized_file(self):
        product = Product.objects.create(
            category=self.category, name="چیپس", price=Decimal("50.00")
        )
        big_file = make_image_file("big.png", size_bytes=MAX_IMAGE_SIZE_BYTES + 1)
        image = ProductImage(product=product, image=big_file)
        with self.assertRaises(Exception):
            image.full_clean()


class BulkPriceUpdateSerializerTests(TestCase):
    def test_rejects_percent_that_would_zero_or_negative_price(self):
        serializer = BulkPriceUpdateSerializer(
            data={"target": "all", "percent": "-100.00"}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("percent", serializer.errors)

    def test_accepts_valid_negative_percent(self):
        serializer = BulkPriceUpdateSerializer(
            data={"target": "all", "percent": "-50.00"}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_accepts_valid_positive_percent(self):
        serializer = BulkPriceUpdateSerializer(
            data={"target": "all", "percent": "20.00"}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)


class ProductImageLimitAPITests(TestCase):
    """
    این تست‌ها فرض می‌کنند permission IsAdmin با یک کاربر ادمین true می‌شود.
    اگر مدل کاربر پروژه با این ساختار فرق دارد، فقط بخش ساخت کاربر ادمین
    را متناسب با apps.users خودتان تغییر دهید.
    """

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="لبنیات")
        self.product = Product.objects.create(
            category=self.category, name="ماست", price=Decimal("30.00")
        )
        try:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            self.admin = User.objects.create_superuser(
                username="admin", email="admin@example.com", password="pass1234"
            )
            self.client.force_authenticate(user=self.admin)
        except Exception:
            self.admin = None

    def test_cannot_upload_more_than_max_images(self):
        if self.admin is None:
            self.skipTest("مدل کاربر پروژه با ساخت پیش‌فرض سازگار نیست.")

        url = reverse("products-images-upload", kwargs={"id": self.product.id})
        files = [make_image_file(f"img{i}.png") for i in range(MAX_IMAGES_PER_PRODUCT + 1)]
        response = self.client.post(url, {"images": files}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.product.images.count(), 0)

    def test_cannot_upload_oversized_image(self):
        if self.admin is None:
            self.skipTest("مدل کاربر پروژه با ساخت پیش‌فرض سازگار نیست.")

        url = reverse("products-images-upload", kwargs={"id": self.product.id})
        big_file = make_image_file("big.png", size_bytes=MAX_IMAGE_SIZE_BYTES + 1)
        response = self.client.post(url, {"images": [big_file]}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.product.images.count(), 0)

    def test_can_upload_up_to_max_images(self):
        if self.admin is None:
            self.skipTest("مدل کاربر پروژه با ساخت پیش‌فرض سازگار نیست.")

        url = reverse("products-images-upload", kwargs={"id": self.product.id})
        files = [make_image_file(f"ok{i}.png") for i in range(MAX_IMAGES_PER_PRODUCT)]
        response = self.client.post(url, {"images": files}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.product.images.count(), MAX_IMAGES_PER_PRODUCT)


class CategoryDetailAPITests(TestCase):
    """رگرسیون‌تست برای باگی که GET روی این endpoint را کرش می‌داد."""

    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="خشکبار")
        try:
            from django.contrib.auth import get_user_model

            User = get_user_model()
            self.admin = User.objects.create_superuser(
                username="admin2", email="admin2@example.com", password="pass1234"
            )
            self.client.force_authenticate(user=self.admin)
        except Exception:
            self.admin = None

    def test_get_category_detail_does_not_crash(self):
        if self.admin is None:
            self.skipTest("مدل کاربر پروژه با ساخت پیش‌فرض سازگار نیست.")

        url = reverse("category-detail", kwargs={"id": self.category.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("products_count", response.data)
