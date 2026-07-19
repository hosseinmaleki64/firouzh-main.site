from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    Customer, Address, Order, OrderItem, Payment, Invoice, OrderStatusHistory,
    OrderStatus, ShippingMethod, PaymentMethod,
)


# =========================================================
# مشتری / آدرس
# =========================================================

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "full_name", "phone", "created_at")


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ("id", "title", "full_address", "postal_code", "is_default", "created_at")


# =========================================================
# آیتم‌های سفارش
# =========================================================

class OrderItemSerializer(serializers.ModelSerializer):
    total_price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ("id", "product", "product_name", "unit_price", "quantity", "total_price")


# =========================================================
# پرداخت / فاکتور
# =========================================================

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id", "method", "status", "amount", "transaction_id", "paid_at")


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ("id", "invoice_number", "pdf_file", "issued_at")


# =========================================================
# تاریخچه وضعیت (تایم‌لاین)
# =========================================================

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    changed_by_name = serializers.CharField(source="changed_by.full_name", read_only=True, default=None)

    class Meta:
        model = OrderStatusHistory
        fields = ("id", "status", "status_display", "changed_by_name", "note", "created_at")


# =========================================================
# لیست سفارشات (جدول - خلاصه)
# =========================================================

class OrderListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    is_event_today = serializers.BooleanField(read_only=True)
    is_delivery_urgent = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = (
            "id", "order_number", "customer_name", "customer_phone",
            "total_amount", "items_count", "status", "status_display",
            "is_event_today", "is_delivery_urgent", "created_at",
        )


# =========================================================
# جزئیات سفارش (پنل کامل)
# =========================================================

class OrderDetailSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    payment = PaymentSerializer(read_only=True)
    invoice = InvoiceSerializer(read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    shipping_method_display = serializers.CharField(source="get_shipping_method_display", read_only=True)
    items_count = serializers.IntegerField(read_only=True)
    is_event_today = serializers.BooleanField(read_only=True)
    is_delivery_urgent = serializers.BooleanField(read_only=True)

    class Meta:
        model = Order
        fields = (
            "id", "order_number", "status", "status_display",
            "customer",
            "shipping_recipient_name", "shipping_recipient_phone",
            "shipping_full_address", "shipping_postal_code",
            "event_time", "delivery_window", "shipping_method", "shipping_method_display",
            "table_arrangement",
            "items", "items_count",
            "items_total", "shipping_cost", "discount_amount", "tax_amount", "total_amount",
            "customer_note", "admin_note",
            "payment", "invoice", "status_history",
            "is_event_today", "is_delivery_urgent",
            "created_at", "updated_at",
        )


# =========================================================
# تغییر وضعیت / یادداشت مدیر
# =========================================================

class ChangeOrderStatusSerializer(serializers.Serializer):
    """
    برای رفتن به وضعیت مشخص (مثلاً لغو سفارش از منوی سه‌نقطه).
    برای «مرحله بعد» در تایم‌لاین از endpoint جدا (advance) استفاده کن که status لازم ندارد.
    """
    status = serializers.ChoiceField(choices=OrderStatus.choices)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class AdvanceStatusSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")


class AdminNoteSerializer(serializers.Serializer):
    admin_note = serializers.CharField(allow_blank=True)


# =========================================================
# ثبت سفارش از روی سبد خرید (تسویه‌حساب مشتری)
# =========================================================

class CheckoutSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=100)
    phone = serializers.CharField(max_length=13)

    recipient_name = serializers.CharField(max_length=100, required=False)
    recipient_phone = serializers.CharField(max_length=13, required=False)
    full_address = serializers.CharField()
    postal_code = serializers.CharField(required=False, allow_blank=True, default="")
    save_address = serializers.BooleanField(default=False)
    address_title = serializers.CharField(required=False, allow_blank=True, default="")

    # زمان تحویل الزامی است (حداقل ۳ روز آینده - همین‌جا سمت سرور هم چک می‌شود)
    event_time = serializers.DateTimeField(required=True)
    delivery_window = serializers.CharField(required=False, allow_blank=True, default="")
    shipping_method = serializers.ChoiceField(choices=ShippingMethod.choices, default=ShippingMethod.COURIER)
    table_arrangement = serializers.CharField(required=False, allow_blank=True, default="")
    customer_note = serializers.CharField(required=False, allow_blank=True, default="")

    coupon_code = serializers.CharField(required=False, allow_blank=True, default="")

    # توجه: shipping_cost / discount_amount / tax_amount دیگر از ورودی کاربر گرفته نمی‌شوند.
    # این مقادیر همیشه سمت سرور در services.create_order_from_cart محاسبه می‌شوند
    # تا کاربر نتواند با دستکاری درخواست، قیمت نهایی را تغییر دهد.
    payment_method = serializers.ChoiceField(choices=PaymentMethod.choices, default=PaymentMethod.ONLINE_GATEWAY)

    def validate(self, attrs):
        attrs.setdefault("recipient_name", attrs["full_name"])
        attrs.setdefault("recipient_phone", attrs["phone"])
        return attrs


class CouponValidateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=30)


class PaymentRequestResponseSerializer(serializers.Serializer):
    payment_url = serializers.URLField()
    order_number = serializers.CharField()
