from decimal import Decimal

from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from apps.authentication.utils import normalize_phone

from .models import (
    Customer, Address, Order, OrderItem, Payment, Invoice, OrderStatusHistory,
    OrderStatus, ALLOWED_TRANSITIONS, STATUS_FLOW, PaymentStatus, PaymentMethod,
    ShippingMethod,
)
from . import pricing
from . import zarinpal
from .zarinpal import ZarinpalError


# =========================================================
# مشتری و آدرس
# =========================================================

def get_or_create_customer(phone: str, full_name: str, user=None) -> Customer:
    """
    مشتری را بر اساس شماره تلفن پیدا می‌کند یا می‌سازد.
    اگر کاربر لاگین کرده باشد (user) و مشتری قبلاً به او وصل نبود، وصلش می‌کند.
    """
    phone = normalize_phone(phone)
    customer, created = Customer.objects.get_or_create(
        phone=phone,
        defaults={"full_name": full_name, "user": user},
    )
    if not created:
        updates = []
        if full_name and customer.full_name != full_name:
            customer.full_name = full_name
            updates.append("full_name")
        if user and customer.user_id is None:
            customer.user = user
            updates.append("user")
        if updates:
            customer.save(update_fields=updates + ["updated_at"])
    return customer


def save_address_for_customer(customer: Customer, *, title="", full_address, postal_code="", is_default=False):
    if is_default:
        customer.addresses.filter(is_default=True).update(is_default=False)
    return Address.objects.create(
        customer=customer,
        title=title,
        full_address=full_address,
        postal_code=postal_code,
        is_default=is_default,
    )


# =========================================================
# ساخت سفارش از روی سبد خرید
# =========================================================

@transaction.atomic
def create_order_from_cart(
    cart,
    *,
    customer: Customer,
    recipient_name: str,
    recipient_phone: str,
    full_address: str,
    postal_code: str = "",
    source_address: Address = None,
    event_time=None,
    delivery_window: str = "",
    shipping_method=None,
    table_arrangement: str = "",
    customer_note: str = "",
    coupon_code: str = "",
    payment_method=None,
):
    """
    سبد خرید را به یک سفارش تبدیل می‌کند: آیتم‌ها اسنپ‌شات می‌شوند.
    هزینه ارسال، مالیات و تخفیف اینجا و فقط اینجا (سمت سرور) محاسبه می‌شوند —
    هیچ مقدار پولی از ورودی کاربر مستقیماً پذیرفته نمی‌شود.
    """
    items = list(cart.items.select_related("product"))
    if not items:
        raise DjangoValidationError("سبد خرید خالی است.")

    pricing.validate_delivery_time(event_time)

    items_total = sum((i.total_price for i in items), start=Decimal("0"))
    shipping_cost = pricing.calculate_shipping_cost(event_time)
    tax_amount = pricing.calculate_tax(items_total)
    discount_amount, coupon = pricing.apply_coupon(coupon_code, items_total)

    total_amount = items_total + shipping_cost + tax_amount - discount_amount

    order = Order.objects.create(
        customer=customer,
        shipping_recipient_name=recipient_name,
        shipping_recipient_phone=normalize_phone(recipient_phone),
        shipping_full_address=full_address,
        shipping_postal_code=postal_code,
        source_address=source_address,
        source_cart=cart,
        event_time=event_time,
        delivery_window=delivery_window,
        shipping_method=shipping_method or ShippingMethod.COURIER,
        table_arrangement=table_arrangement,
        customer_note=customer_note,
        items_total=items_total,
        shipping_cost=shipping_cost,
        discount_amount=discount_amount,
        tax_amount=tax_amount,
        total_amount=total_amount,
        status=OrderStatus.PENDING_PAYMENT,
    )

    OrderItem.objects.bulk_create([
        OrderItem(
            order=order,
            product=i.product,
            product_name=i.product.name,
            unit_price=i.unit_price,
            quantity=i.quantity,
        )
        for i in items
    ])

    from django.conf import settings as django_settings

    Payment.objects.create(
        order=order,
        method=payment_method or PaymentMethod.ONLINE_GATEWAY,
        status=PaymentStatus.PENDING,
        amount=total_amount,
        is_sandbox=getattr(django_settings, "ZARINPAL_SANDBOX", True),
    )

    if coupon is not None:
        coupon.used_count += 1
        coupon.save(update_fields=["used_count"])

    OrderStatusHistory.objects.create(
        order=order, status=OrderStatus.PENDING_PAYMENT, changed_by=None,
        note="سفارش ثبت شد.",
    )

    # سبد خرید مصرف شده؛ دیگر فعال نیست
    from apps.cart.models import CartStatus
    cart.status = CartStatus.ORDERED
    cart.save(update_fields=["status", "updated_at"])

    return order


# =========================================================
# تغییر وضعیت سفارش
# =========================================================

def advance_status(order: Order, *, changed_by=None, note: str = "") -> Order:
    """
    سفارش را یک مرحله در مسیر خطیِ تایم‌لاین جلو می‌برد (دکمه «مرحله بعد»).
    """
    try:
        current_index = STATUS_FLOW.index(order.status)
    except ValueError:
        raise DjangoValidationError("این سفارش در وضعیتی است که مرحله بعدی برایش تعریف نشده (مثلاً لغو شده).")

    if current_index + 1 >= len(STATUS_FLOW):
        raise DjangoValidationError("سفارش در آخرین مرحله (تحویل شده) قرار دارد.")

    next_status = STATUS_FLOW[current_index + 1]
    return set_status(order, next_status, changed_by=changed_by, note=note)


def set_status(order: Order, new_status: str, *, changed_by=None, note: str = "") -> Order:
    """
    سفارش را به‌طور صریح به یک وضعیت مشخص می‌برد (مثلاً لغو سفارش)،
    فقط اگر گذار مجاز باشد.
    """
    allowed = ALLOWED_TRANSITIONS.get(order.status, [])
    if new_status not in allowed:
        raise DjangoValidationError(
            f"انتقال از «{order.get_status_display()}» به «{OrderStatus(new_status).label}» مجاز نیست."
        )

    with transaction.atomic():
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])

        OrderStatusHistory.objects.create(
            order=order, status=new_status, changed_by=changed_by, note=note,
        )

        if new_status == OrderStatus.PAID and hasattr(order, "payment"):
            payment = order.payment
            payment.status = PaymentStatus.SUCCESS
            payment.paid_at = timezone.now()
            payment.save(update_fields=["status", "paid_at", "updated_at"])

        if new_status == OrderStatus.CANCELLED and hasattr(order, "payment"):
            payment = order.payment
            if payment.status == PaymentStatus.SUCCESS:
                payment.status = PaymentStatus.REFUNDED
                payment.save(update_fields=["status", "updated_at"])

    return order


def cancel_order(order: Order, *, changed_by=None, note: str = "") -> Order:
    return set_status(order, OrderStatus.CANCELLED, changed_by=changed_by, note=note or "سفارش لغو شد.")


def update_admin_note(order: Order, note: str) -> Order:
    order.admin_note = note
    order.save(update_fields=["admin_note", "updated_at"])
    return order


def ensure_invoice(order: Order) -> Invoice:
    """
    فاکتور را در صورت نبود می‌سازد (تولید فایل PDF واقعی بعداً وصل می‌شود).
    """
    invoice, _ = Invoice.objects.get_or_create(order=order)
    return invoice


# =========================================================
# درگاه پرداخت (زرین‌پال)
# =========================================================

def start_gateway_payment(order: Order, *, callback_url: str) -> str:
    """
    برای سفارش PENDING_PAYMENT از زرین‌پال Authority می‌گیرد و URL پرداخت را برمی‌گرداند.
    """
    if order.status != OrderStatus.PENDING_PAYMENT:
        raise DjangoValidationError("این سفارش در وضعیت قابل پرداخت نیست.")

    payment = getattr(order, "payment", None)
    if payment is None:
        raise DjangoValidationError("رکورد پرداخت برای این سفارش پیدا نشد.")

    if payment.status == PaymentStatus.SUCCESS:
        raise DjangoValidationError("این سفارش قبلاً پرداخت شده است.")

    try:
        authority = zarinpal.request_payment(
            amount=order.total_amount,
            description=f"سفارش فینگرفود فیروزه #{order.order_number}",
            callback_url=callback_url,
            mobile=order.shipping_recipient_phone,
        )
    except ZarinpalError as e:
        raise DjangoValidationError(str(e))

    payment.gateway_authority = authority
    payment.save(update_fields=["gateway_authority", "updated_at"])

    return zarinpal.get_payment_redirect_url(authority)


def finalize_gateway_payment(*, authority: str, gateway_status: str) -> Order:
    """
    وقتی کاربر از زرین‌پال به callback_url برمی‌گردد این تابع صدا زده می‌شود.
    اگر Status=OK باشد پرداخت verify می‌شود، در غیر این صورت سفارش لغو می‌شود.
    """
    payment = Payment.objects.select_related("order").filter(gateway_authority=authority).first()
    if payment is None:
        raise DjangoValidationError("تراکنشی با این شناسه پیدا نشد.")

    order = payment.order

    # اگر قبلاً verify شده (مثلاً کاربر صفحه را رفرش کرده)، دوباره کاری لازم نیست
    if payment.status == PaymentStatus.SUCCESS:
        return order

    if gateway_status != "OK":
        set_status(order, OrderStatus.CANCELLED, note="پرداخت توسط کاربر لغو یا ناموفق بود.")
        payment.status = PaymentStatus.FAILED
        payment.save(update_fields=["status", "updated_at"])
        return order

    try:
        ref_id = zarinpal.verify_payment(amount=order.total_amount, authority=authority)
    except ZarinpalError as e:
        # پرداخت تایید نشد؛ سفارش را لغو نمی‌کنیم چون ممکن است مشکل موقتی شبکه باشد،
        # فقط PENDING می‌ماند تا بعداً به‌صورت دستی یا با retry بررسی شود.
        payment.gateway_response = {"error": str(e)}
        payment.save(update_fields=["gateway_response", "updated_at"])
        raise DjangoValidationError(f"تایید پرداخت با خطا مواجه شد: {e}")

    payment.status = PaymentStatus.SUCCESS
    payment.transaction_id = ref_id
    payment.paid_at = timezone.now()
    payment.save(update_fields=["status", "transaction_id", "paid_at", "updated_at"])

    set_status(order, OrderStatus.PAID, note=f"پرداخت آنلاین با کد پیگیری {ref_id} تایید شد.")

    return order
