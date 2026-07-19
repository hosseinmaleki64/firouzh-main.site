from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.orders"

    def ready(self):
        # سیگنال‌ها (اگر لازم شد) اینجا وصل می‌شوند
        pass
