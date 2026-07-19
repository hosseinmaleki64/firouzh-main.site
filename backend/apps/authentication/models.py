import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from .utils import normalize_phone
from .validators import validate_iranian_phone


class UserRole(models.TextChoices):
    USER = "USER", "User"
    ADMIN = "ADMIN", "Admin"
    SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"


class UserManager(BaseUserManager):

    def create_user(self, phone, full_name, password=None, **extra_fields):

        if not phone:
            raise ValueError("Phone number is required")
        phone = normalize_phone(phone)
        validate_iranian_phone(phone)
            

        user = self.model(
            phone=phone,
            full_name=full_name,
            **extra_fields
        )

        user.set_password(password)

        user.save(using=self._db)

        return user

    def create_superuser(self, phone, full_name, password=None, **extra_fields):

        extra_fields.setdefault("role", UserRole.SUPER_ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        
        if extra_fields.get("is_staff") is not True:
           raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(
            phone,
            full_name,
            password,
            **extra_fields
        )


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    phone = models.CharField(
        max_length=13,
        unique=True,
        validators=[validate_iranian_phone],
    )

    full_name = models.CharField(
        max_length=100,
    )

    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
    )

    phone_verified = models.BooleanField(
    default=False,  
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_staff = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    objects = UserManager()

    USERNAME_FIELD = "phone"

    REQUIRED_FIELDS = ["full_name"]

    def __str__(self):
        return self.full_name