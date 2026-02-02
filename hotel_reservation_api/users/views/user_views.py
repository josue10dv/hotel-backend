from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model

User = get_user_model()
from users.serializers import (
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    UserRegistrationSerializer,
)
from app.utilities import (
    success_response,
    created_response,
    validation_error_response,
    list_response,
    check_is_owner_or_staff,
    check_is_owner,
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operaciones CRUD completas sobre el modelo User.

    Endpoints disponibles:
    - POST /api/users/                       → Registrar nuevo usuario (público)
    - GET /api/users/                        → Listar todos los usuarios (autenticado)
    - GET /api/users/{id}/                   → Obtener usuario específico
    - GET /api/users/me/                     → Obtener usuario actual
    - PUT /api/users/{id}/                   → Actualización completa de usuario
    - PATCH /api/users/{id}/                 → Actualización parcial de usuario
    - DELETE /api/users/{id}/                → Desactivar usuario
    - POST /api/users/{id}/change-password/  → Cambiar contraseña
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Retorna el serializador apropiado según la acción."""
        if self.action == "create":
            return UserRegistrationSerializer
        elif self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        elif self.action == "change_password":
            return ChangePasswordSerializer
        return UserSerializer

    def get_permissions(self):
        """Retorna permisos personalizados según la acción."""
        if self.action == "create":
            return [AllowAny()]  # Registro público
        return [IsAuthenticated()]  # El resto requiere autenticación
    
    def create(self, request):
        """
        Registra un nuevo usuario en el sistema.

        Body de la petición:
            {
                "username": "string",
                "email": "string",
                "password": "string",
                "password_confirm": "string"
            }
        """
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        user = serializer.save()
        return created_response(
            data={
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            message='User registered successfully'
        )
    
    def list(self, request):
        """Lista todos los usuarios en el sistema."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return list_response(serializer.data, count=queryset.count())

    def retrieve(self, request, pk=None):
        """Obtiene los detalles de un usuario específico por ID."""
        user = self.get_object()
        serializer = self.get_serializer(user)
        return success_response(data=serializer.data)
    
    def update(self, request, pk=None):
        """Actualiza completamente un usuario (PUT)."""
        user = self.get_object()

        # Verificar permisos: solo el propietario o staff puede actualizar
        permission_error = check_is_owner_or_staff(request.user, user.id)
        if permission_error:
            return permission_error
        
        serializer = self.get_serializer(user, data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        serializer.save()
        return success_response(
            data=serializer.data,
            message='Usuario actualizado exitosamente'
        )
    
    def partial_update(self, request, pk=None):
        """Actualiza parcialmente un usuario (PATCH)."""
        user = self.get_object()

        # Verificar permisos: solo el propietario o staff puede actualizar
        permission_error = check_is_owner_or_staff(request.user, user.id)
        if permission_error:
            return permission_error
        
        serializer = self.get_serializer(user, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        serializer.save()
        return success_response(
            data=serializer.data,
            message='Usuario actualizado exitosamente'
        )
    
    def destroy(self, request, pk=None):
        """
        Elimina lógicamente un usuario desactivando la cuenta.

        No elimina físicamente el registro, solo lo desactiva.
        """
        user = self.get_object()

        # Verificar permisos: solo el propietario o staff puede eliminar
        permission_error = check_is_owner_or_staff(request.user, user.id)
        if permission_error:
            return permission_error

        # Eliminación lógica: desactivar en lugar de eliminar
        user.is_active = False
        user.save()

        return success_response(
            message='Cuenta de usuario desactivada exitosamente',
            status_code=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=["post"], url_path="change-password")
    def change_password(self, request, pk=None):
        """
        Cambia la contraseña del usuario.

        Endpoint: POST /api/users/{id}/change-password/

        Body de la petición:
            {
                "old_password": "string",
                "new_password": "string",
                "new_password_confirm": "string"
            }
        """
        user = self.get_object()

        # Solo el usuario puede cambiar su propia contraseña (verificación estricta)
        permission_error = check_is_owner(
            request.user, 
            user.id, 
            'Solo puedes cambiar tu propia contraseña'
        )
        if permission_error:
            return permission_error

        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        serializer.save()
        return success_response(message='Contraseña cambiada exitosamente')
    
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """
        Obtiene el usuario autenticado actual.

        Endpoint: GET /api/users/me/
        """
        serializer = self.get_serializer(request.user)
        return success_response(data=serializer.data)
    
    @action(detail=False, methods=["get"], url_path="dashboard-stats")
    def dashboard_stats(self, request):
        """
        Obtiene estadísticas del dashboard para usuarios tipo guest.

        Endpoint: GET /api/users/dashboard-stats/
        """
        from reservations.services.reservation_service import ReservationService
        from wishlist.services.wishlist_service import WishlistService
        from reviews.services.review_service import ReviewService
        from datetime import datetime
        
        user_id = str(request.user.id)
        
        # Get reservation service
        reservation_service = ReservationService()
        wishlist_service = WishlistService()
        review_service = ReviewService()
        
        # Get reservations count
        try:
            all_reservations = reservation_service.get_user_reservations(user_id)
            total_reservations = len(all_reservations)
            
            # Count upcoming reservations
            upcoming_reservations = len([
                r for r in all_reservations 
                if r.get('status') in ['pending', 'confirmed'] and 
                datetime.fromisoformat(r.get('check_in_date', '').replace('Z', '+00:00')) > datetime.now()
            ])
            
            # Calculate total spent
            total_spent = sum([
                float(r.get('total_price', 0)) 
                for r in all_reservations 
                if r.get('status') in ['confirmed', 'completed']
            ])
        except Exception:
            total_reservations = 0
            upcoming_reservations = 0
            total_spent = 0.0
        
        # Get wishlist count
        try:
            wishlist = wishlist_service.get_wishlist(user_id)
            favorite_hotels_count = len(wishlist.get('hotels', []))
        except Exception:
            favorite_hotels_count = 0
        
        # Get reviews count
        try:
            user_reviews = review_service.get_user_reviews(user_id)
            reviews_written = len(user_reviews)
        except Exception:
            reviews_written = 0
        
        return success_response(data={
            'total_reservations': total_reservations,
            'upcoming_reservations': upcoming_reservations,
            'total_spent': round(total_spent, 2),
            'favorite_hotels_count': favorite_hotels_count,
            'reviews_written': reviews_written
        })
    
    @action(detail=False, methods=["get"], url_path="owner-dashboard-stats")
    def owner_dashboard_stats(self, request):
        """
        Obtiene estadísticas del dashboard para usuarios tipo owner.

        Endpoint: GET /api/users/owner-dashboard-stats/
        Permissions: user_type = 'owner'
        """
        from hotels.services.hotel_service import HotelService
        from reservations.services.reservation_service import ReservationService
        from reviews.services.review_service import ReviewService
        from datetime import datetime, timedelta
        from app.mongodb import get_hotels_collection
        
        # Verify user is owner
        if request.user.user_type != 'owner':
            return validation_error_response({
                'permission': ['Only owners can access this endpoint']
            })
        
        user_id = str(request.user.id)
        
        # Get services
        hotel_service = HotelService()
        reservation_service = ReservationService()
        review_service = ReviewService()
        
        # Get owner's hotels
        try:
            owner_hotels = hotel_service.get_hotels_by_owner(user_id)
            total_hotels = len(owner_hotels)
            
            # Count total rooms
            total_rooms = sum([len(hotel.get('rooms', [])) for hotel in owner_hotels])
            
            # Get hotel IDs
            hotel_ids = [str(hotel.get('_id')) for hotel in owner_hotels]
        except Exception:
            total_hotels = 0
            total_rooms = 0
            hotel_ids = []
        
        # Get reservations for owner's hotels
        try:
            hotels_collection = get_hotels_collection()
            all_reservations = []
            
            for hotel_id in hotel_ids:
                try:
                    reservations = reservation_service.get_reservations_by_hotel(hotel_id)
                    all_reservations.extend(reservations)
                except Exception:
                    continue
            
            # Count active reservations
            active_reservations = len([
                r for r in all_reservations 
                if r.get('status') in ['pending', 'confirmed']
            ])
            
            # Calculate monthly earnings (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            monthly_earnings = sum([
                float(r.get('total_price', 0)) 
                for r in all_reservations 
                if r.get('status') in ['confirmed', 'completed'] and
                datetime.fromisoformat(r.get('created_at', '').replace('Z', '+00:00')) > thirty_days_ago
            ])
        except Exception:
            active_reservations = 0
            monthly_earnings = 0.0
        
        # Get reviews statistics
        try:
            total_reviews = 0
            total_rating = 0.0
            
            for hotel in owner_hotels:
                hotel_rating = hotel.get('rating', 0)
                hotel_reviews_count = hotel.get('total_reviews', 0)
                total_reviews += hotel_reviews_count
                total_rating += hotel_rating * hotel_reviews_count if hotel_reviews_count > 0 else 0
            
            average_rating = round(total_rating / total_reviews, 2) if total_reviews > 0 else 0.0
        except Exception:
            total_reviews = 0
            average_rating = 0.0
        
        # Calculate occupancy rate (simplified)
        try:
            if total_rooms > 0:
                occupied_rooms = len([r for r in all_reservations if r.get('status') in ['confirmed', 'completed']])
                occupancy_rate = round((occupied_rooms / (total_rooms * 30)) * 100, 2)  # Last 30 days
            else:
                occupancy_rate = 0.0
        except Exception:
            occupancy_rate = 0.0
        
        return success_response(data={
            'total_hotels': total_hotels,
            'total_rooms': total_rooms,
            'active_reservations': active_reservations,
            'monthly_earnings': round(monthly_earnings, 2),
            'total_reviews': total_reviews,
            'average_rating': average_rating,
            'occupancy_rate': min(occupancy_rate, 100.0)  # Cap at 100%
        })
