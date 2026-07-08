from apps.authentication.models import User


def get_users():
    return User.objects.all().order_by("-created_at")


def get_user_by_id(user_id):
    return User.objects.get(id=user_id)