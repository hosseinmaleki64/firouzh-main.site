from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Cart, CartItem, CartStatus, CART_EXPIRY_DAYS


def get_or_create_cart(request):
    """
    اگر کاربر لاگین باشد (JWT معتبر → request.user.is_authenticated) بر اساس user،
    وگرنه بر اساس session_key سبد را پیدا/می‌سازد.
    """
    if request.user and request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(
            user=request.user,
            status=CartStatus.ACTIVE,
            defaults={"expires_at": timezone.now() + timedelta(days=CART_EXPIRY_DAYS)},
        )
        return cart

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    cart, _ = Cart.objects.get_or_create(
        session_key=session_key,
        user=None,
        status=CartStatus.ACTIVE,
        defaults={"expires_at": timezone.now() + timedelta(days=CART_EXPIRY_DAYS)},
    )
    return cart


def get_cart_item_or_404(cart, item_id):
    """
    کاربر فقط به آیتم‌های سبد خودش دسترسی دارد؛ حتی اگر id درست را حدس بزند
    ولی متعلق به سبد دیگری باشد، 404 می‌گیرد.
    """
    return get_object_or_404(CartItem, id=item_id, cart=cart)


def add_product(cart, product, quantity=1):
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={"quantity": quantity, "unit_price": product.final_price},
    )
    if not created:
        item.quantity += quantity
        item.save(update_fields=["quantity", "updated_at"])

    cart.touch()
    return item


def update_quantity(item: CartItem, new_quantity: int):
    """
    مقدار مطلق را ست می‌کند. اگر صفر یا منفی باشد، آیتم حذف می‌شود.
    """
    cart = item.cart
    if new_quantity <= 0:
        item.delete()
        cart.touch()
        return None

    item.quantity = new_quantity
    item.save(update_fields=["quantity", "updated_at"])
    cart.touch()
    return item


def increase_quantity(item: CartItem):
    return update_quantity(item, item.quantity + 1)


def decrease_quantity(item: CartItem):
    return update_quantity(item, item.quantity - 1)  # اگر برسد به ۰، خودش حذف می‌کند


def remove_product(item: CartItem):
    cart = item.cart
    item.delete()
    cart.touch()


def clear_cart(cart: Cart):
    cart.items.all().delete()
    cart.touch()


def calculate_total(cart: Cart):
    items = list(cart.items.select_related("product"))
    subtotal = sum((i.total_price for i in items), start=0)
    total_items = sum((i.quantity for i in items), start=0)
    return {
        "total_items": total_items,
        "subtotal": subtotal,
        # هزینه ارسال/تخفیف/مالیات در فاز Order اضافه می‌شود؛ فعلاً total == subtotal
        "total": subtotal,
    }


def merge_guest_cart_into_user(request, user):
    """
    وقتی کاربر مهمان لاگین می‌کند، سبد session را با سبد user ادغام می‌کند.
    این تابع را باید داخل LoginSerializer/LoginAPIView صدا بزنی (بعداً وصلش می‌کنیم).
    """
    session_key = request.session.session_key
    if not session_key:
        return

    try:
        guest_cart = Cart.objects.get(session_key=session_key, user=None, status=CartStatus.ACTIVE)
    except Cart.DoesNotExist:
        return

    user_cart, _ = Cart.objects.get_or_create(
        user=user,
        status=CartStatus.ACTIVE,
        defaults={"expires_at": timezone.now() + timedelta(days=CART_EXPIRY_DAYS)},
    )

    for guest_item in guest_cart.items.all():
        add_product(user_cart, guest_item.product, guest_item.quantity)

    guest_cart.delete()