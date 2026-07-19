from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from . import services
from .serializers import CartSerializer, AddToCartSerializer, UpdateQuantitySerializer


class CartAPIView(APIView):
    """
    GET /api/cart/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        cart = services.get_or_create_cart(request)
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class AddToCartAPIView(APIView):
    """
    POST /api/cart/items/
    body: { "product_id": "...", "quantity": 1 }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = services.get_or_create_cart(request)
        product = serializer.get_product()
        services.add_product(cart, product, serializer.validated_data["quantity"])

        cart.refresh_from_db()
        return Response(CartSerializer(cart).data, status=status.HTTP_201_CREATED)


class CartItemDetailAPIView(APIView):
    """
    یک مسیر، دو متد — دقیقاً مطابق مستند:
    PATCH  /api/cart/items/{id}/   body: { "quantity": 3 }   (0 یعنی حذف آیتم)
    DELETE /api/cart/items/{id}/
    """
    permission_classes = [AllowAny]

    def patch(self, request, id):
        serializer = UpdateQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = services.get_or_create_cart(request)
        item = services.get_cart_item_or_404(cart, id)
        services.update_quantity(item, serializer.validated_data["quantity"])

        cart.refresh_from_db()
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)

    def delete(self, request, id):
        cart = services.get_or_create_cart(request)
        item = services.get_cart_item_or_404(cart, id)
        services.remove_product(item)

        cart.refresh_from_db()
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)


class ClearCartAPIView(APIView):
    """
    DELETE /api/cart/clear/
    """
    permission_classes = [AllowAny]

    def delete(self, request):
        cart = services.get_or_create_cart(request)
        services.clear_cart(cart)

        cart.refresh_from_db()
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)