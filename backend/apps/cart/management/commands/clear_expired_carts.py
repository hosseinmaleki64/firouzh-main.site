from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cart.models import Cart, CartStatus


class Command(BaseCommand):
    help = "سبدهای خرید فعالی که منقضی شده‌اند (بدون فعالیت) را حذف می‌کند."

    def handle(self, *args, **options):
        expired = Cart.objects.filter(
            status=CartStatus.ACTIVE,
            expires_at__lt=timezone.now(),
        )
        count = expired.count()
        expired.delete()
        self.stdout.write(self.style.SUCCESS(f"{count} سبد خرید منقضی‌شده حذف شد."))