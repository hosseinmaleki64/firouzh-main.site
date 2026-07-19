import django_filters
from .models import Product


class ProductFilter(django_filters.FilterSet):
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Product
        fields = ["category", "is_active"]


class PublicProductFilter(django_filters.FilterSet):
    """
    فیلتر endpointهای عمومی (سایت اصلی). برخلاف ProductFilter ادمین،
    اینجا فیلد is_active وجود ندارد تا کاربر سایت نتواند با
    ?is_active=false محصولات غیرفعال را ببیند.
    """
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Product
        fields = ["category"]