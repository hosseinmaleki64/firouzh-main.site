from rest_framework import generics
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import IsAuthenticated

from apps.authentication.models import User
from .serializers import DashboardUserSerializer
from .permissions import IsAdminOrSuperAdmin


class UserListAPIView(generics.ListAPIView):
    queryset = User.objects.all().order_by("-created_at")
    serializer_class = DashboardUserSerializer

    permission_classes = [
        IsAuthenticated,
        IsAdminOrSuperAdmin,
    ]

    filter_backends = [
        SearchFilter,
        OrderingFilter,
    ]

    search_fields = [
        "full_name",
        "phone",
    ]

    ordering_fields = [
        "created_at",
        "full_name",
    ]