import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import Order, OrderStatus


class OrderFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=OrderStatus.choices)

    # بازه دلخواه
    date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    # میانبرهای تاریخ: today, yesterday, this_week, this_month
    quick_date = django_filters.CharFilter(method="filter_quick_date")

    # جستجو در شماره سفارش، نام و تلفن مشتری
    search = django_filters.CharFilter(method="filter_search")

    urgent_first = django_filters.BooleanFilter(method="filter_noop")  # فقط پرچم، ordering در view انجام می‌شود

    class Meta:
        model = Order
        fields = ["status"]

    def filter_noop(self, qs, name, value):
        return qs

    def filter_search(self, qs, name, value):
        if not value:
            return qs
        return qs.filter(
            Q(order_number__icontains=value)
            | Q(customer__full_name__icontains=value)
            | Q(customer__phone__icontains=value)
            | Q(shipping_recipient_phone__icontains=value)
        )

    def filter_quick_date(self, qs, name, value):
        now = timezone.localtime()
        today = now.date()

        if value == "today":
            return qs.filter(created_at__date=today)
        if value == "yesterday":
            return qs.filter(created_at__date=today - timezone.timedelta(days=1))
        if value == "this_week":
            start_of_week = today - timezone.timedelta(days=today.weekday())
            return qs.filter(created_at__date__gte=start_of_week)
        if value == "this_month":
            return qs.filter(created_at__year=today.year, created_at__month=today.month)

        return qs
