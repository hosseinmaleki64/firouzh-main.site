from rest_framework import serializers
from apps.authentication.models import User


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "phone",
            "role",
            "is_active",
            "phone_verified",
            "created_at",
        )


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "phone",
            "role",
            "is_active",
            "phone_verified",
            "created_at",
            "updated_at",
        )


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    فقط ویرایش نام و وضعیت فعال/غیرفعال.
    عمداً فیلد role اینجا نیست — تغییر نقش فقط از طریق
    make-admin / remove-admin انجام می‌شود.
    """
    class Meta:
        model = User
        fields = (
            "full_name",
            "is_active",
        )


class UserStatisticsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    admins = serializers.IntegerField()
    new_today = serializers.IntegerField()