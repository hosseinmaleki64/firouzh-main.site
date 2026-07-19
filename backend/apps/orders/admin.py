from django.contrib import admin
from .models import Customer, Address, Order, OrderItem, Payment, Invoice, OrderStatusHistory, Coupon


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "value", "is_active", "used_count", "usage_limit", "valid_until")
    list_filter = ("discount_type", "is_active")
    search_fields = ("code",)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "user", "created_at")
    search_fields = ("full_name", "phone")


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0


admin.site.register(Address)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "unit_price", "quantity")


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ("status", "changed_by", "note", "created_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number", "customer", "status", "total_amount",
        "shipping_method", "created_at",
    )
    list_filter = ("status", "shipping_method")
    search_fields = ("order_number", "customer__full_name", "customer__phone")
    readonly_fields = ("id", "order_number", "created_at", "updated_at")
    inlines = [OrderItemInline, OrderStatusHistoryInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "method", "status", "amount", "is_sandbox", "gateway_authority", "transaction_id", "paid_at")
    list_filter = ("method", "status", "is_sandbox")
    search_fields = ("gateway_authority", "transaction_id", "order__order_number")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "order", "issued_at")
