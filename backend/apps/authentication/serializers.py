from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User, UserRole
from .utils import normalize_phone
from .validators import validate_iranian_phone


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "full_name",
            "phone",
            "password",
            "confirm_password",
        )

    def validate_phone(self, value):
        try:
            phone = normalize_phone(value)
            validate_iranian_phone(phone)
        except (ValueError, DjangoValidationError) as e:
            # normalize_phone -> ValueError | validate_iranian_phone -> ValidationError
            message = e.messages[0] if isinstance(e, DjangoValidationError) else str(e)
            raise serializers.ValidationError(message)

        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("این شماره قبلاً ثبت شده است.")

        return phone

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        try:
            # چک یکتا بودن شماره در validate_phone و ساخت واقعی کاربر اینجا
            # دو عملیات جدا روی دیتابیس‌اند؛ اگر دو درخواست همزمان با یک شماره
            # بیایند، هر دو از آن چک رد می‌شوند و یکی‌شان اینجا با
            # IntegrityError مواجه می‌شود. آن را به یک خطای ۴۰۰ تمیز تبدیل می‌کنیم
            # به‌جای اینکه به یک ۵۰۰ خام تبدیل شود.
            return User.objects.create_user(**validated_data)
        except IntegrityError:
            raise serializers.ValidationError(
                {"phone": "این شماره قبلاً ثبت شده است."}
            )


class LoginSerializer(TokenObtainPairSerializer):
    phone = serializers.CharField()

    def validate(self, attrs):
        phone = attrs.get("phone")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            phone=phone,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError(
                "Phone number or password is incorrect."
            )

        refresh = self.get_token(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "phone",
            "role",
            "phone_verified",
            "created_at",
        )


class AdminLoginSerializer(TokenObtainPairSerializer):
    phone = serializers.CharField()

    def validate(self, attrs):
        phone = attrs.get("phone")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            phone=phone,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError(
                "شماره موبایل یا رمز عبور اشتباه است."
            )

        if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
            raise serializers.ValidationError(
                "دسترسی به پنل مدیریت مجاز نیست."
            )

        if not user.is_active:
            raise serializers.ValidationError("حساب کاربری غیرفعال است.")

        refresh = self.get_token(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": UserProfileSerializer(user).data,
        }
