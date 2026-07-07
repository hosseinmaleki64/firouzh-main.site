from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("phone", "full_name", "role", "phone_verified", "is_active", "created_at")
    search_fields = ("phone", "full_name")
    list_filter = ("role", "is_active", "phone_verified")
    readonly_fields = ("id", "created_at", "updated_at")