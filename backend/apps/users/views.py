from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from apps.authentication.models import User, UserRole

from .serializers import (
    UserListSerializer,
    UserDetailSerializer,
    UserUpdateSerializer,
)
from .selectors import get_users
from .permissions import IsAdmin, IsSuperAdmin
from .pagination import UserPagination


class UserListAPIView(generics.ListAPIView):
    serializer_class = UserListSerializer
    permission_classes = [IsAdmin]
    pagination_class = UserPagination

    def get_queryset(self):
        return get_users()

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]

    filterset_fields = ["role", "is_active"]

    search_fields = [
        "full_name",
        "phone",
    ]

    ordering_fields = [
        "created_at",
        "full_name",
    ]

    ordering = [
        "-created_at",
    ]


class UserDetailAPIView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/users/{id}/  -> جزئیات کاربر
    PATCH /api/users/{id}/  -> ویرایش نام / وضعیت فعال‌بودن

    نکته امنیتی: حتی اگر کسی از فرانت مقدار role را در بدنه‌ی
    درخواست PATCH بفرستد، UserUpdateSerializer اصلاً آن فیلد را
    نمی‌شناسد و نادیده گرفته می‌شود. علاوه بر آن، ویرایش حساب
    SUPER_ADMIN از این مسیر کاملاً مسدود است.
    """
    permission_classes = [IsAdmin]
    lookup_field = "id"
    lookup_url_kwarg = "id"
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return UserUpdateSerializer
        return UserDetailSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.role == UserRole.SUPER_ADMIN:
            return Response(
                {"detail": "حساب مدیر ارشد از پنل قابل ویرایش نیست."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().update(request, *args, **kwargs)


class MakeAdminAPIView(APIView):
    """
    POST /api/users/{id}/make-admin/
    فقط SUPER_ADMIN مجاز است. کاربر USER را به ADMIN تبدیل می‌کند.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, id):
        user = get_object_or_404(User, id=id)

        if user.role == UserRole.SUPER_ADMIN:
            return Response(
                {"detail": "نقش مدیر ارشد قابل تغییر نیست."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.role == UserRole.ADMIN:
            return Response(
                {"detail": "این کاربر از قبل مدیر است."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.role = UserRole.ADMIN
        user.save(update_fields=["role", "updated_at"])

        return Response(
            UserDetailSerializer(user).data,
            status=status.HTTP_200_OK,
        )


class RemoveAdminAPIView(APIView):
    """
    POST /api/users/{id}/remove-admin/
    فقط SUPER_ADMIN مجاز است. دسترسی مدیریت را از ADMIN می‌گیرد
    و نقش را به USER برمی‌گرداند.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request, id):
        user = get_object_or_404(User, id=id)

        if user.role == UserRole.SUPER_ADMIN:
            return Response(
                {"detail": "نقش مدیر ارشد قابل تغییر نیست."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.role != UserRole.ADMIN:
            return Response(
                {"detail": "این کاربر مدیر نیست."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.role = UserRole.USER
        user.save(update_fields=["role", "updated_at"])

        return Response(
            UserDetailSerializer(user).data,
            status=status.HTTP_200_OK,
        )