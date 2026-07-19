from django.urls import path
from .views import (
    ProductStatsAPIView,
    CategoryListAPIView,
    CategoryDetailAPIView,
    ProductListCreateAPIView,
    ProductDetailAPIView,
    ProductImageUploadAPIView,
    ProductImageDeleteAPIView,
    BulkPriceUpdateAPIView,
    BulkDiscountAPIView,
    PublicCategoryListAPIView,
    PublicProductListAPIView,
    PublicProductDetailAPIView,
)

urlpatterns = [
    path("stats/", ProductStatsAPIView.as_view(), name="products-stats"),

    # دسته‌بندی‌ها (ادمین)
    path("categories/", CategoryListAPIView.as_view(), name="categories-list"),
    path("categories/<uuid:id>/", CategoryDetailAPIView.as_view(), name="category-detail"),

    # محصولات (ادمین)
    path("<uuid:id>/", ProductDetailAPIView.as_view(), name="products-detail"),
    path("<uuid:id>/images/", ProductImageUploadAPIView.as_view(), name="products-images-upload"),
    path("<uuid:id>/images/<uuid:image_id>/", ProductImageDeleteAPIView.as_view(), name="products-images-delete"),

    path("bulk-price-update/", BulkPriceUpdateAPIView.as_view(), name="products-bulk-price"),
    path("bulk-discount/", BulkDiscountAPIView.as_view(), name="products-bulk-discount"),

    # عمومی (بدون نیاز به لاگین — سایت اصلی)
    path("public/categories/", PublicCategoryListAPIView.as_view(), name="public-categories"),
    path("public/<uuid:id>/", PublicProductDetailAPIView.as_view(), name="public-product-detail"),
    path("public/", PublicProductListAPIView.as_view(), name="public-products-list"),

    # این باید همیشه آخرین pattern این فایل باشه چون خالی‌ترین الگوئه (فقط /api/products/)
    path("", ProductListCreateAPIView.as_view(), name="products-list-create"),
]