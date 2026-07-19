from django.urls import path
from .views import (
    OrderStatsAPIView,
    OrderListAPIView,
    OrderDetailAPIView,
    OrderAdvanceStatusAPIView,
    OrderChangeStatusAPIView,
    OrderCancelAPIView,
    OrderAdminNoteAPIView,
    OrderInvoiceAPIView,
    CheckoutAPIView,
    CouponValidateAPIView,
    PaymentRequestAPIView,
    PaymentCallbackAPIView,
)

urlpatterns = [
    path("stats/", OrderStatsAPIView.as_view(), name="orders-stats"),

    # تسویه‌حساب مشتری (سبد خرید -> سفارش)
    path("checkout/", CheckoutAPIView.as_view(), name="orders-checkout"),
    path("coupons/validate/", CouponValidateAPIView.as_view(), name="orders-coupon-validate"),

    # درگاه پرداخت زرین‌پال
    # نکته: این باید قبل از الگوی "<uuid:id>/" بیاید تا "payment/callback/" با آن اشتباه گرفته نشود
    path("payment/callback/", PaymentCallbackAPIView.as_view(), name="orders-payment-callback"),
    path("<uuid:id>/pay/", PaymentRequestAPIView.as_view(), name="orders-payment-request"),

    # پنل ادمین
    path("<uuid:id>/advance-status/", OrderAdvanceStatusAPIView.as_view(), name="orders-advance-status"),
    path("<uuid:id>/change-status/", OrderChangeStatusAPIView.as_view(), name="orders-change-status"),
    path("<uuid:id>/cancel/", OrderCancelAPIView.as_view(), name="orders-cancel"),
    path("<uuid:id>/admin-note/", OrderAdminNoteAPIView.as_view(), name="orders-admin-note"),
    path("<uuid:id>/invoice/", OrderInvoiceAPIView.as_view(), name="orders-invoice"),
    path("<uuid:id>/", OrderDetailAPIView.as_view(), name="orders-detail"),

    # این باید همیشه آخرین pattern این فایل باشد چون خالی‌ترین الگوست (فقط /api/orders/)
    path("", OrderListAPIView.as_view(), name="orders-list"),
]
