"""
Vistas para la funcionalidad de wishlist.
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from bson import ObjectId

from app.utilities.responses import success_response, error_response
from wishlist.services import WishlistService
from wishlist.serializers import (
    WishlistSerializer,
    AddToWishlistSerializer
)


class WishlistView(APIView):
    """
    Vista para obtener la wishlist completa del usuario autenticado.
    
    GET /api/wishlist/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Obtiene la wishlist del usuario con todos los hoteles."""
        try:
            user_id = str(request.user.id)
            service = WishlistService()
            
            wishlist_data = service.get_wishlist_with_hotels(user_id)
            serializer = WishlistSerializer(wishlist_data)
            
            return success_response(
                data=serializer.data,
                message="Wishlist obtenida exitosamente"
            )
        except Exception as e:
            return error_response(
                message="Error al obtener wishlist",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AddToWishlistView(APIView):
    """
    Vista para agregar un hotel a la wishlist.
    
    POST /api/wishlist/add/
    Body: {"hotel_id": "..."}
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Agrega un hotel a la wishlist del usuario."""
        serializer = AddToWishlistSerializer(data=request.data)
        
        if not serializer.is_valid():
            return error_response(
                message="Datos inválidos",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_id = str(request.user.id)
            hotel_id = serializer.validated_data["hotel_id"]
            
            service = WishlistService()
            result = service.add_hotel(user_id, hotel_id)
            
            return success_response(
                data=result,
                message="Hotel agregado a la wishlist",
                status_code=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(
                message="Error al agregar hotel a wishlist",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RemoveFromWishlistView(APIView):
    """
    Vista para eliminar un hotel de la wishlist.
    
    DELETE /api/wishlist/remove/{hotel_id}/
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, hotel_id):
        """Elimina un hotel de la wishlist del usuario."""
        # Validar que hotel_id sea un ObjectId válido
        try:
            ObjectId(hotel_id)
        except Exception:
            return error_response(
                message="ID de hotel inválido",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_id = str(request.user.id)
            service = WishlistService()
            
            result = service.remove_hotel(user_id, hotel_id)
            
            return success_response(
                data=result,
                message="Hotel eliminado de la wishlist"
            )
        except ValueError as e:
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(
                message="Error al eliminar hotel de wishlist",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CheckWishlistView(APIView):
    """
    Vista para verificar si un hotel está en la wishlist del usuario.
    
    GET /api/wishlist/check/{hotel_id}/
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, hotel_id):
        """Verifica si un hotel está en la wishlist."""
        # Validar que hotel_id sea un ObjectId válido
        try:
            ObjectId(hotel_id)
        except Exception:
            return error_response(
                message="ID de hotel inválido",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_id = str(request.user.id)
            service = WishlistService()
            
            in_wishlist = service.is_hotel_in_wishlist(user_id, hotel_id)
            
            return success_response(
                data={
                    "hotel_id": hotel_id,
                    "in_wishlist": in_wishlist
                },
                message="Verificación completada"
            )
        except Exception as e:
            return error_response(
                message="Error al verificar wishlist",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ClearWishlistView(APIView):
    """
    Vista para limpiar completamente la wishlist del usuario.
    
    DELETE /api/wishlist/clear/
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request):
        """Elimina todos los hoteles de la wishlist del usuario."""
        try:
            user_id = str(request.user.id)
            service = WishlistService()
            
            result = service.clear_wishlist(user_id)
            
            return success_response(
                data=result,
                message="Wishlist limpiada exitosamente"
            )
        except Exception as e:
            return error_response(
                message="Error al limpiar wishlist",
                errors=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
