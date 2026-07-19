from django.db.models import Count, Sum, Q
from django.utils import timezone

from .models import Order, OrderStatus


def get_orders_base_qs():
    return (
        Order.objects.select_related("customer", "payment", "invoice")
        .prefetch_related("items", "status_history")
    )


def get_order_detail_qs():
    return get_orders_base_qs()


def get_dashboard_stats():
    qs = Order.objects.all()
    return {
        "total_orders": qs.count(),
        "pending_confirmation": qs.filter(
            status__in=[OrderStatus.PENDING_PAYMENT, OrderStatus.PAID]
        ).count(),
        "preparing": qs.filter(status=OrderStatus.PREPARING).count(),
        "shipped": qs.filter(status=OrderStatus.SHIPPED).count(),
        "delivered": qs.filter(status=OrderStatus.DELIVERED).count(),
        "cancelled": qs.filter(status=OrderStatus.CANCELLED).count(),
    }
