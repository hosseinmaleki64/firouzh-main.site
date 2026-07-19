from django.db.models import Count, Q
from .models import Product, Category


def get_products():
    return Product.objects.select_related("category").prefetch_related("images")


def get_categories_with_counts():
    return Category.objects.annotate(
        products_count=Count("products", filter=Q(products__is_active=True))
    )


def get_products_by_bulk_target(data):
    """
    برای افزایش قیمت گروهی / تخفیف گروهی از این تابع استفاده می‌شود.
    فقط روی محصولات فعال اعمال می‌شود.
    """
    qs = Product.objects.filter(is_active=True)
    target = data["target"]

    if target == "category":
        qs = qs.filter(category_id=data["category_id"])
    elif target == "manual":
        qs = qs.filter(id__in=data["product_ids"])
    elif target == "search":
        qs = qs.filter(Q(name__icontains=data["search"]))
    # target == "all" یعنی همین qs پایه کافیست

    return qs