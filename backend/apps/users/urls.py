from django.urls import path
from .views import (
    UserListAPIView,
    UserDetailAPIView,
    MakeAdminAPIView,
    RemoveAdminAPIView,
)

urlpatterns = [
    path("", UserListAPIView.as_view(), name="users-list"),
    path("<uuid:id>/", UserDetailAPIView.as_view(), name="users-detail"),
    path("<uuid:id>/make-admin/", MakeAdminAPIView.as_view(), name="users-make-admin"),
    path("<uuid:id>/remove-admin/", RemoveAdminAPIView.as_view(), name="users-remove-admin"),
]