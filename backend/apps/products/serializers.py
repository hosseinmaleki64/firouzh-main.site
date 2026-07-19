from decimal import Decimal
from rest_framework import serializers
from .models import Product, ProductImage, Category, WeightUnit


class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ("id", "name", "image", "products_count", "created_at")


class CategoryMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "image")


class CategoryWriteSerializer(serializers.ModelSerializer):
    """
    برای ویرایش مستقیم یک دسته‌بندیِ از قبل موجود (اسم/عکس/فعال‌بودن)،
    مستقل از ساخت یا ویرایش محصول. از طریق CategoryDetailAPIView استفاده می‌شود.
    """
    class Meta:
        model = Category
        fields = ("name", "image", "is_active")


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image")


class ProductListSerializer(serializers.ModelSerializer):
    category = CategoryMiniSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id", "name", "description", "price", "discount_percent",
            "final_price", "weight_value", "weight_unit",
            "raw_materials", "components",
            "category", "images", "is_active", "created_at",
        )

    def get_final_price(self, obj):
        return obj.final_price


class ProductWriteSerializer(serializers.ModelSerializer):
    """
    برای ساخت و ویرایش محصول.
    دسته‌بندی یا با category_id (موجود) یا با new_category_name (جدید) مشخص می‌شود.
    اگر دسته‌بندی جدید ساخته می‌شود، new_category_image هم می‌تواند همان لحظه
    عکس آن دسته‌بندی تازه را تنظیم کند.
    عکس‌های محصول اینجا نیستند — از endpoint جدا آپلود می‌شوند چون multipart را ساده‌تر می‌کند.
    """
    category_id = serializers.UUIDField(required=False, allow_null=True)
    new_category_name = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    new_category_image = serializers.ImageField(
        required=False, allow_null=True, write_only=True
    )

    class Meta:
        model = Product
        fields = (
            "name", "description", "price", "discount_percent",
            "weight_value", "weight_unit",
            "raw_materials", "components", "is_active",
            "category_id", "new_category_name", "new_category_image",
        )

    def validate_weight_unit(self, value):
        if value and value not in WeightUnit.values:
            raise serializers.ValidationError("واحد وزن نامعتبر است.")
        return value

    def validate_discount_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("درصد تخفیف باید بین ۰ تا ۱۰۰ باشد.")
        return value

    def validate(self, attrs):
        creating = self.instance is None
        category_id = attrs.get("category_id")
        new_name = attrs.get("new_category_name", "").strip() if attrs.get("new_category_name") else ""

        if category_id and new_name:
            raise serializers.ValidationError(
                "فقط یکی از «دسته‌بندی موجود» یا «دسته‌بندی جدید» را مشخص کنید."
            )

        if creating and not category_id and not new_name:
            raise serializers.ValidationError(
                "باید یک دسته‌بندی انتخاب کنید یا نام دسته‌بندی جدید را بدهید."
            )

        if category_id:
            try:
                attrs["category"] = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                raise serializers.ValidationError({"category_id": "دسته‌بندی پیدا نشد."})

        attrs.pop("category_id", None)
        if new_name:
            attrs["new_category_name"] = new_name
        else:
            # اگر دسته‌بندی جدید نمی‌سازیم، عکس دسته‌بندی جدید هم بی‌معنی است
            attrs.pop("new_category_image", None)

        return attrs

    def _resolve_category(self, validated_data):
        new_name = validated_data.pop("new_category_name", "")
        new_image = validated_data.pop("new_category_image", None)
        category = validated_data.pop("category", None)
        if new_name:
            category, created = Category.objects.get_or_create(name=new_name)
            if new_image:
                category.image = new_image
                category.save(update_fields=["image"])
        return category, validated_data

    def create(self, validated_data):
        category, validated_data = self._resolve_category(validated_data)
        return Product.objects.create(category=category, **validated_data)

    def update(self, instance, validated_data):
        category, validated_data = self._resolve_category(validated_data)
        if category:
            instance.category = category
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class BulkTargetSerializer(serializers.Serializer):
    """
    مبنای مشترک برای افزایش قیمت گروهی و تخفیف گروهی.
    """
    target = serializers.ChoiceField(choices=["all", "category", "manual", "search"])
    category_id = serializers.UUIDField(required=False)
    product_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False
    )
    search = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        target = attrs["target"]
        if target == "category" and not attrs.get("category_id"):
            raise serializers.ValidationError({"category_id": "دسته‌بندی را انتخاب کنید."})
        if target == "manual" and not attrs.get("product_ids"):
            raise serializers.ValidationError({"product_ids": "حداقل یک محصول انتخاب کنید."})
        if target == "search" and not attrs.get("search", "").strip():
            raise serializers.ValidationError({"search": "عبارت جستجو را وارد کنید."})
        return attrs


class BulkPriceUpdateSerializer(BulkTargetSerializer):
    percent = serializers.DecimalField(max_digits=6, decimal_places=2)
    round_to_integer = serializers.BooleanField(default=False)

    def validate_percent(self, value):
        # percent <= -100 یعنی قیمت جدید صفر یا منفی می‌شود؛ مجاز نیست.
        if value <= Decimal("-100"):
            raise serializers.ValidationError(
                "درصد نمی‌تواند طوری باشد که قیمت نهایی صفر یا منفی شود (حداقل -99.99)."
            )
        return value


class BulkDiscountSerializer(BulkTargetSerializer):
    percent = serializers.DecimalField(max_digits=5, decimal_places=2)

    def validate_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("درصد تخفیف باید بین ۰ تا ۱۰۰ باشد.")
        return value


class ProductStatsSerializer(serializers.Serializer):
    total_products = serializers.IntegerField()
    total_categories = serializers.IntegerField()