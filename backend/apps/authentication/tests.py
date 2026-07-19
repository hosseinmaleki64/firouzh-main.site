from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import User, UserRole
from .validators import validate_iranian_phone


class PhoneValidatorTests(TestCase):
    def test_valid_phone_passes(self):
        # نباید استثنا بدهد
        validate_iranian_phone("+989121234567")

    def test_invalid_phone_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            validate_iranian_phone("09121234567")  # نرمال‌نشده

        with self.assertRaises(ValidationError):
            validate_iranian_phone("+981234567890")  # پیش‌شماره غلط


class RegisterAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("register")

    def _payload(self, **overrides):
        data = {
            "full_name": "علی رضایی",
            "phone": "09121234567",
            "password": "StrongPass123",
            "confirm_password": "StrongPass123",
        }
        data.update(overrides)
        return data

    def test_register_success(self):
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(phone="+989121234567").exists())

    def test_register_invalid_phone_returns_400_not_500(self):
        response = self.client.post(self.url, self._payload(phone="abc"), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_password_mismatch(self):
        response = self.client.post(
            self.url, self._payload(confirm_password="different"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_phone_returns_400_not_500(self):
        User.objects.create_user(
            phone="09121234567", full_name="کاربر قبلی", password="StrongPass123"
        )
        response = self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone", response.data)


class LoginAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("login")
        self.user = User.objects.create_user(
            phone="09121234567", full_name="کاربر تست", password="StrongPass123"
        )

    def test_login_success(self):
        response = self.client.post(
            self.url,
            {"phone": "09121234567", "password": "StrongPass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_wrong_password_returns_400_not_500(self):
        response = self.client.post(
            self.url,
            {"phone": "09121234567", "password": "wrongpass"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_malformed_phone_returns_400_not_500(self):
        """
        رگرسیون‌تست برای باگی که با فرمت غلط شماره (مثلاً 'abc')
        باعث کرش 500 در PhoneBackend.authenticate می‌شد.
        """
        response = self.client.post(
            self.url,
            {"phone": "abc", "password": "whatever"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AdminLoginAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("admin-login")
        self.normal_user = User.objects.create_user(
            phone="09121234567", full_name="کاربر عادی", password="StrongPass123"
        )
        self.admin_user = User.objects.create_user(
            phone="09129876543",
            full_name="ادمین",
            password="StrongPass123",
            role=UserRole.ADMIN,
        )

    def test_normal_user_cannot_admin_login(self):
        response = self.client.post(
            self.url,
            {"phone": "09121234567", "password": "StrongPass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_user_can_admin_login(self):
        response = self.client.post(
            self.url,
            {"phone": "09129876543", "password": "StrongPass123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("user", response.data)
