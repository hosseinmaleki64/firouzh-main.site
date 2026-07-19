from django.urls import path
from .views import (
    CartAPIView,
    AddToCartAPIView,
    CartItemDetailAPIView,
    ClearCartAPIView,
)

urlpatterns = [
    path("", CartAPIView.as_view(), name="cart-detail"),
    path("items/", AddToCartAPIView.as_view(), name="cart-add-item"),
    path("items/<uuid:id>/", CartItemDetailAPIView.as_view(), name="cart-item-detail"),  # PATCH و DELETE
    path("clear/", ClearCartAPIView.as_view(), name="cart-clear"),
]