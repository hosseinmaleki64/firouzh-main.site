from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from .models import Product, ProductImage, Category
from .filters import ProductFilter, PublicProductFilter
from .pagination import ProductPagination
from .permissions import IsAdmin
from .selectors import get_products, get_categories_with_counts, get_products_by_bulk_target
from .validators import (
    validate_image_size,
    MAX_IMAGE_SIZE_MB,
    MAX_IMAGES_PER_PRODUCT,
)
from .serializers import (
    ProductListSerializer,
    ProductWriteSerializer,
    ProductImageSerializer,
    CategorySerializer,
    CategoryWriteSerializer,
    BulkPriceUpdateSerializer,
    BulkDiscountSerializer,
)


def _validate_images(files, existing_count=0):
    """
    files: لیست فایل‌های آپلودشده (request.FILES.getlist(...))
    existing_count: تعداد عکس‌هایی که محصول از قبل دارد (برای آپلود جداگانه)

    بررسی می‌کند که:
    - مجموع عکس‌ها از MAX_IMAGES_PER_PRODUCT بیشتر نشود
    - حجم هیچ عکسی از MAX_IMAGE_SIZE_MB بیشتر نشود
    در صورت خطا، رشته‌ی پیام خطا برمی‌گرداند؛ در غیر این صورت None.
    """
    if existing_count + len(files) > MAX_IMAGES_PER_PRODUCT:
        return f"هر محصول حداکثر می‌تواند {MAX_IMAGES_PER_PRODUCT} عکس داشته باشد."

    for f in files:
        try:
            validate_image_size(f)
        except Exception:
            return f"حجم هر عکس نباید بیشتر از {MAX_IMAGE_SIZE_MB} مگابایت باشد. (فایل: {f.name})"

    return None


class ProductStatsAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({
            "total_products": Product.objects.filter(is_active=True).count(),
            "total_categories": Category.objects.count(),
        })


class CategoryListAPIView(generics.ListAPIView):
    """
    برای نمایش لیست دسته‌بندی‌های موجود (هم توی فیلتر لیست محصولات،
    هم توی فرم «افزودن محصول» برای انتخاب از دسته‌بندی‌های قبلی).
    ادمین‌فقط.
    """
    serializer_class = CategorySerializer
    permission_classes = [IsAdmin]
    pagination_class = None  # دسته‌بندی‌ها معمولاً کم‌اند، همه یکجا برمی‌گردد

    def get_queryset(self):
        return get_categories_with_counts()


class CategoryDetailAPIView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/products/categories/{id}/
    برای ویرایش مستقیم نام/عکس/فعال‌بودن یک دسته‌بندیِ از قبل موجود
    (مثلاً فقط عوض کردن عکسش)، بدون نیاز به ساخت یا ویرایش محصول. ادمین‌فقط.
    """
    permission_classes = [IsAdmin]
    lookup_field = "id"
    lookup_url_kwarg = "id"
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        # CategorySerializer (برای GET) به فیلد annotate شده‌ی products_count نیاز دارد؛
        # بدون این annotate، درخواست GET با AttributeError خطا می‌داد.
        if self.request.method in ("PATCH", "PUT"):
            return Category.objects.all()
        return get_categories_with_counts()

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return CategoryWriteSerializer
        return CategorySerializer


class ProductListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdmin]
    pagination_class = ProductPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "price", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return get_products()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProductWriteSerializer
        return ProductListSerializer

    def create(self, request, *args, **kwargs):
        # اعتبارسنجی تعداد/حجم عکس‌ها قبل از ساخت محصول، تا در صورت خطا
        # محصولی بدون عکس یا با عکس ناقص در دیتابیس باقی نماند.
        images = request.FILES.getlist("images")
        error = _validate_images(images)
        if error:
            return Response({"images": [error]}, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        product = serializer.save()
        for image_file in self.request.FILES.getlist("images"):
            ProductImage.objects.create(product=product, image=image_file)


class ProductDetailAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdmin]
    lookup_field = "id"
    lookup_url_kwarg = "id"
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    queryset = Product.objects.all()

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return ProductWriteSerializer
        return ProductListSerializer


class ProductImageUploadAPIView(APIView):
    """
    POST /api/products/{id}/images/   (multipart, فیلد 'images' — می‌تواند چندتایی باشد)
    """
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, id):
        product = get_object_or_404(Product, id=id)
        files = request.FILES.getlist("images")
        if not files:
            return Response({"detail": "هیچ عکسی ارسال نشده."}, status=status.HTTP_400_BAD_REQUEST)

        existing_count = product.images.count()
        error = _validate_images(files, existing_count=existing_count)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        created = [ProductImage.objects.create(product=product, image=f) for f in files]
        return Response(
            ProductImageSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class ProductImageDeleteAPIView(APIView):
    permission_classes = [IsAdmin]

    def delete(self, request, id, image_id):
        image = get_object_or_404(ProductImage, id=image_id, product_id=id)
        image.image.delete(save=False)  # حذف فایل از دیسک
        image.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BulkPriceUpdateAPIView(APIView):
    """
    POST /api/products/bulk-price-update/
    body: { target, category_id?, product_ids?, search?, percent, round_to_integer }
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = BulkPriceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        qs = get_products_by_bulk_target(data)
        percent = data["percent"]
        round_it = data.get("round_to_integer", False)

        updated = 0
        with transaction.atomic():
            for product in qs.select_for_update():
                new_price = product.price * (Decimal("1") + percent / Decimal("100"))
                if round_it:
                    new_price = new_price.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                else:
                    new_price = new_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                product.price = new_price
                product.save(update_fields=["price", "updated_at"])
                updated += 1

        return Response({"updated_count": updated}, status=status.HTTP_200_OK)


class BulkDiscountAPIView(APIView):
    """
    POST /api/products/bulk-discount/
    body: { target, category_id?, product_ids?, search?, percent }
    percent همان درصد تخفیفی است که روی discount_percent ست می‌شود.
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = BulkDiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        qs = get_products_by_bulk_target(data)
        updated = qs.update(discount_percent=data["percent"])

        return Response({"updated_count": updated}, status=status.HTTP_200_OK)


# =========================================================
# Endpointهای عمومی (بدون نیاز به لاگین) — برای سایت اصلی
# =========================================================

class PublicCategoryListAPIView(generics.ListAPIView):
    """
    GET /api/products/public/categories/
    فقط دسته‌بندی‌هایی که حداقل یک محصول فعال دارند برمی‌گردد
    (برای ساخت سایدبار/گرید دسته‌بندی در سایت اصلی).
    """
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        return get_categories_with_counts().filter(products_count__gt=0)


class PublicProductListAPIView(generics.ListAPIView):
    """
    GET /api/products/public/
    فقط محصولات فعال؛ is_active قابل override از سمت کلاینت نیست.
    """
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    pagination_class = ProductPagination

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = PublicProductFilter
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "price", "name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return Product.objects.filter(is_active=True).select_related("category").prefetch_related("images")


class PublicProductDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/products/public/{id}/
    برای صفحه‌ی جزئیات محصول (product.html?id=...) در سایت اصلی.
    """
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    lookup_field = "id"
    queryset = Product.objects.filter(is_active=True)