from rest_framework import serializers
from apps.authentication.models import User


class DashboardUserSerializer(serializers.ModelSerializer):
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