from rest_framework import serializers

from apps.products.models import Product
from .models import CartItem, Cart


class CartItemProductSerializer(serializers.ModelSerializer):
    """
    نمای خلاصه‌ی محصول، فقط چیزی که سبد خرید لازم دارد.
    """
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ("id", "name", "price", "final_price", "image", "is_active")

    def get_image(self, obj):
        first = obj.images.first()
        return first.image.url if first else None


class CartItemSerializer(serializers.ModelSerializer):
    product = CartItemProductSerializer(read_only=True)
    total_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ("id", "product", "quantity", "unit_price", "total_price")


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ("id", "items", "total_items", "subtotal", "total")

    def _totals(self, obj):
        # از context کش می‌کنیم تا سه بار جداگانه محاسبه نشود
        if not hasattr(self, "_cached_totals"):
            from .services import calculate_total
            self._cached_totals = calculate_total(obj)
        return self._cached_totals

    def get_total_items(self, obj):
        return self._totals(obj)["total_items"]

    def get_subtotal(self, obj):
        return self._totals(obj)["subtotal"]

    def get_total(self, obj):
        return self._totals(obj)["total"]


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(id=value, is_active=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError("محصول پیدا نشد یا در دسترس نیست.")
        self._product = product
        return value

    def get_product(self):
        return self._product


class UpdateQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=0)  # صفر یعنی حذف آیتم