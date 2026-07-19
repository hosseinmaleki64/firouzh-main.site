from decimal import Decimal

from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.products.models import Category, Product
from apps.cart.models import Cart, CartItem, CartStatus

from .models import Customer, Order, OrderStatus
from . import services


class OrderStatusTransitionTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="کیک")
        self.product = Product.objects.create(
            category=self.category, name="کیک شکلاتی", price=Decimal("500000")
        )
        self.cart = Cart.objects.create(session_key="test-session")
        CartItem.objects.create(
            cart=self.cart, product=self.product, quantity=2, unit_price=self.product.price
        )
        self.customer = Customer.objects.create(full_name="حسین ملکی", phone="+989141234567")

    def _create_order(self):
        return services.create_order_from_cart(
            self.cart,
            customer=self.customer,
            recipient_name="حسین ملکی",
            recipient_phone="+989141234567",
            full_address="تهران، خیابان آزادی",
        )

    def test_create_order_from_cart_snapshots_items_and_totals(self):
        order = self._create_order()
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items_total, Decimal("1000000"))
        self.assertEqual(order.total_amount, Decimal("1000000"))
        self.assertEqual(order.status, OrderStatus.PENDING_PAYMENT)
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.status, CartStatus.ORDERED)

    def test_advance_status_moves_one_step_forward(self):
        order = self._create_order()
        services.advance_status(order)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PAID)
        self.assertEqual(order.status_history.count(), 2)

    def test_invalid_transition_is_rejected(self):
        order = self._create_order()
        with self.assertRaises(ValidationError):
            services.set_status(order, OrderStatus.SHIPPED)

    def test_cancel_from_preparing_is_allowed(self):
        order = self._create_order()
        for _ in range(3):  # PENDING -> PAID -> CONFIRMED -> PREPARING
            services.advance_status(order)
            order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PREPARING)

        services.cancel_order(order)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)

    def test_cancel_from_delivered_is_rejected(self):
        order = self._create_order()
        for _ in range(6):  # تا DELIVERED
            services.advance_status(order)
            order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.DELIVERED)

        with self.assertRaises(ValidationError):
            services.cancel_order(order)
