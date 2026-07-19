from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.cart import services as cart_services

from . import services
from .filters import OrderFilter
from .models import Order
from .pagination import OrderPagination
from .permissions import IsAdmin
from .selectors import get_orders_base_qs, get_order_detail_qs, get_dashboard_stats
from .serializers import (
    OrderListSerializer, OrderDetailSerializer,
    ChangeOrderStatusSerializer, AdvanceStatusSerializer, AdminNoteSerializer,
    CheckoutSerializer, InvoiceSerializer,
    CouponValidateSerializer, PaymentRequestResponseSerializer,
)
from . import pricing
from .models import OrderStatus


def _django_error_to_drf(exc: DjangoValidationError):
    message = exc.message if hasattr(exc, "message") else str(exc)
    raise DRFValidationError({"detail": message})


# =========================================================
# داشبورد ادمین
# =========================================================

class OrderStatsAPIView(APIView):
    """
    GET /api/orders/stats/  -> کارت‌های آمار بالای صفحه
    """
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(get_dashboard_stats(), status=status.HTTP_200_OK)


class OrderListAPIView(generics.ListAPIView):
    """
    GET /api/orders/
    پشتیبانی از: search, status, quick_date, date_from/date_to, urgent_first, ordering
    """
    serializer_class = OrderListSerializer
    permission_classes = [IsAdmin]
    pagination_class = OrderPagination

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = OrderFilter
    ordering_fields = ["created_at", "total_amount", "event_time"]
    ordering = ["-created_at"]

    def get_queryset(self):
        qs = get_orders_base_qs()
        if self.request.query_params.get("urgent_first") == "true":
            # سفارش‌هایی که کمتر از دو ساعت تا مراسمشان مانده، اول لیست بیایند
            from django.utils import timezone
            from django.db.models import Case, When, Value, IntegerField
            now = timezone.now()
            soon = now + timezone.timedelta(hours=2)
            qs = qs.annotate(
                _urgent=Case(
                    When(event_time__isnull=False, event_time__gte=now, event_time__lte=soon, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            ).order_by("_urgent", "-created_at")
        return qs


class OrderDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/orders/{id}/
    """
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAdmin]
    lookup_field = "id"
    lookup_url_kwarg = "id"

    def get_queryset(self):
        return get_order_detail_qs()


class OrderAdvanceStatusAPIView(APIView):
    """
    POST /api/orders/{id}/advance-status/
    یک مرحله در تایم‌لاین جلو می‌رود (دکمه «مرحله بعد»).
    """
    permission_classes = [IsAdmin]

    def post(self, request, id):
        order = get_object_or_404(Order, id=id)
        serializer = AdvanceStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            services.advance_status(
                order, changed_by=request.user, note=serializer.validated_data["note"]
            )
        except DjangoValidationError as e:
            _django_error_to_drf(e)

        order.refresh_from_db()
        return Response(OrderDetailSerializer(order).data, status=status.HTTP_200_OK)


class OrderChangeStatusAPIView(APIView):
    """
    POST /api/orders/{id}/change-status/
    body: { "status": "CANCELLED", "note": "..." }
    برای پرش صریح به یک وضعیت (مثلاً لغو سفارش از منوی سه‌نقطه).
    """
    permission_classes = [IsAdmin]

    def post(self, request, id):
        order = get_object_or_404(Order, id=id)
        serializer = ChangeOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            services.set_status(
                order,
                serializer.validated_data["status"],
                changed_by=request.user,
                note=serializer.validated_data["note"],
            )
        except DjangoValidationError as e:
            _django_error_to_drf(e)

        order.refresh_from_db()
        return Response(OrderDetailSerializer(order).data, status=status.HTTP_200_OK)


class OrderCancelAPIView(APIView):
    """
    POST /api/orders/{id}/cancel/
    """
    permission_classes = [IsAdmin]

    def post(self, request, id):
        order = get_object_or_404(Order, id=id)
        note = request.data.get("note", "")
        try:
            services.cancel_order(order, changed_by=request.user, note=note)
        except DjangoValidationError as e:
            _django_error_to_drf(e)

        order.refresh_from_db()
        return Response(OrderDetailSerializer(order).data, status=status.HTTP_200_OK)


class OrderAdminNoteAPIView(APIView):
    """
    PATCH /api/orders/{id}/admin-note/
    body: { "admin_note": "..." }
    این یادداشت هرگز به مشتری نمایش داده نمی‌شود.
    """
    permission_classes = [IsAdmin]

    def patch(self, request, id):
        order = get_object_or_404(Order, id=id)
        serializer = AdminNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        services.update_admin_note(order, serializer.validated_data["admin_note"])
        return Response(OrderDetailSerializer(order).data, status=status.HTTP_200_OK)


class OrderInvoiceAPIView(APIView):
    """
    GET /api/orders/{id}/invoice/
    داده‌ی فاکتور را برمی‌گرداند (رندر PDF واقعی بعداً، هنگام اتصال به فرانت، اضافه می‌شود).
    """
    permission_classes = [IsAdmin]

    def get(self, request, id):
        order = get_object_or_404(Order, id=id)
        invoice = services.ensure_invoice(order)
        return Response({
            "invoice": InvoiceSerializer(invoice).data,
            "order": OrderDetailSerializer(order).data,
        })


# =========================================================
# تسویه‌حساب مشتری (تبدیل سبد خرید به سفارش)
# =========================================================

class CheckoutAPIView(APIView):
    """
    POST /api/orders/checkout/
    سبد خرید فعلی کاربر/مهمان (بر اساس user یا session) را به سفارش تبدیل می‌کند.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cart = cart_services.get_or_create_cart(request)

        customer = services.get_or_create_customer(
            phone=data["phone"],
            full_name=data["full_name"],
            user=request.user if request.user.is_authenticated else None,
        )

        source_address = None
        if data["save_address"]:
            source_address = services.save_address_for_customer(
                customer,
                title=data["address_title"],
                full_address=data["full_address"],
                postal_code=data["postal_code"],
            )

        try:
            order = services.create_order_from_cart(
                cart,
                customer=customer,
                recipient_name=data["recipient_name"],
                recipient_phone=data["recipient_phone"],
                full_address=data["full_address"],
                postal_code=data["postal_code"],
                source_address=source_address,
                event_time=data.get("event_time"),
                delivery_window=data["delivery_window"],
                shipping_method=data["shipping_method"],
                table_arrangement=data["table_arrangement"],
                customer_note=data["customer_note"],
                coupon_code=data["coupon_code"],
                payment_method=data["payment_method"],
            )
        except DjangoValidationError as e:
            _django_error_to_drf(e)

        return Response(OrderDetailSerializer(order).data, status=status.HTTP_201_CREATED)


# =========================================================
# اعتبارسنجی کد تخفیف (پیش‌نمایش قبل از ثبت نهایی سفارش)
# =========================================================

class CouponValidateAPIView(APIView):
    """
    POST /api/orders/coupons/validate/   body: { "code": "..." }
    روی سبد خرید فعلی کاربر/مهمان چک می‌کند و مبلغ تخفیف را برای پیش‌نمایش UI برمی‌گرداند.
    مقدار قطعی و نهایی باز هم در لحظه‌ی ثبت سفارش (checkout) دوباره محاسبه می‌شود.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CouponValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = cart_services.get_or_create_cart(request)
        subtotal = cart.subtotal if hasattr(cart, "subtotal") else sum(
            (i.total_price for i in cart.items.all()), start=0
        )

        try:
            discount_amount, coupon = pricing.apply_coupon(serializer.validated_data["code"], subtotal)
        except DjangoValidationError as e:
            _django_error_to_drf(e)

        return Response({
            "valid": True,
            "code": coupon.code,
            "discount_amount": discount_amount,
            "subtotal": subtotal,
        })


# =========================================================
# درگاه پرداخت (زرین‌پال)
# =========================================================

class PaymentRequestAPIView(APIView):
    """
    POST /api/orders/{id}/pay/
    سفارش باید از قبل با /checkout/ ساخته شده و در وضعیت PENDING_PAYMENT باشد.
    خروجی: آدرس ریدایرکت به درگاه زرین‌پال (sandbox یا real، بسته به تنظیمات).
    """
    permission_classes = [AllowAny]

    def post(self, request, id):
        order = get_object_or_404(Order, id=id)
        callback_url = request.build_absolute_uri("/api/orders/payment/callback/")

        try:
            payment_url = services.start_gateway_payment(order, callback_url=callback_url)
        except DjangoValidationError as e:
            _django_error_to_drf(e)

        data = PaymentRequestResponseSerializer({
            "payment_url": payment_url,
            "order_number": order.order_number,
        }).data
        return Response(data, status=status.HTTP_200_OK)


class PaymentCallbackAPIView(APIView):
    """
    GET /api/orders/payment/callback/?Authority=...&Status=OK
    زرین‌پال کاربر را مستقیماً به همین آدرس ریدایرکت می‌کند (نه یک فراخوانی از فرانت ما).
    بعد از verify، کاربر را به صفحه‌ی نتیجه در فرانت هدایت می‌کنیم.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from django.conf import settings
        from django.shortcuts import redirect

        authority = request.query_params.get("Authority", "")
        gateway_status = request.query_params.get("Status", "")
        result_base = getattr(settings, "FRONTEND_ORDER_RESULT_URL", "/order-result.html")

        try:
            order = services.finalize_gateway_payment(authority=authority, gateway_status=gateway_status)
        except DjangoValidationError as e:
            message = e.message if hasattr(e, "message") else str(e)
            return redirect(f"{result_base}?status=error&message={message}")

        outcome = "success" if order.status == OrderStatus.PAID else "failed"
        return redirect(f"{result_base}?status={outcome}&order_number={order.order_number}")
