from django.contrib.auth.backends import ModelBackend
from .models import User
from .utils import normalize_phone


class PhoneBackend(ModelBackend):
    def authenticate(self, request, phone=None, password=None, **kwargs):

        if phone is None:
            return None

        phone = normalize_phone(phone)

        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None