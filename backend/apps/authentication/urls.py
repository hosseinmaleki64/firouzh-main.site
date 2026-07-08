from django.urls import path
from .views import RegisterAPIView, LoginAPIView,AdminLoginAPIView, ProfileAPIView
from rest_framework_simplejwt.views import TokenRefreshView


urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("admin-login/", AdminLoginAPIView.as_view(), name="admin-login"),
    path("profile/", ProfileAPIView.as_view(), name="profile"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
