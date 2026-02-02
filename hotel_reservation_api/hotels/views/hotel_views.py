"""
Vistas para la gestión de hoteles.

Implementa endpoints REST usando ViewSets de Django REST Framework.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from hotels.serializers import (
    HotelSerializer,
    HotelListSerializer,
    HotelCreateSerializer,
    HotelUpdateSerializer,
    RoomSerializer,
)
from hotels.services.hotel_service import HotelService
from app.utilities import (
    created_response,
    success_response,
    validation_error_response,
    not_found_response,
    parse_pagination_params,
    extract_filters_from_params,
)


class HotelViewSet(viewsets.ViewSet):
    """
    ViewSet para operaciones CRUD de hoteles.
    
    Endpoints disponibles:
    - POST /api/hotels/                          → Crear hotel (autenticado)
    - GET /api/hotels/                           → Listar todos los hoteles (público)
    - GET /api/hotels/{id}/                      → Obtener detalle de hotel (público)
    - PUT /api/hotels/{id}/                      → Actualizar hotel completo (propietario)
    - PATCH /api/hotels/{id}/                    → Actualizar hotel parcial (propietario)
    - DELETE /api/hotels/{id}/                   → Eliminar hotel (propietario)
    - GET /api/hotels/my-hotels/                 → Hoteles del usuario autenticado
    - POST /api/hotels/{id}/add-room/            → Agregar habitación (propietario)
    - PUT /api/hotels/{id}/update-room/{room_id}/ → Actualizar habitación (propietario)
    - DELETE /api/hotels/{id}/delete-room/{room_id}/ → Eliminar habitación (propietario)
    - GET /api/hotels/search/                    → Búsqueda de hoteles (público)
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hotel_service = HotelService()
    
    def get_permissions(self):
        """
        Define permisos según la acción.
        
        Acciones públicas: list, retrieve, search
        Acciones autenticadas: create, update, destroy, operaciones de habitaciones
        """
        if self.action in ['list', 'retrieve', 'search']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def create(self, request):
        """
        Crea un nuevo hotel.
        
        POST /api/hotels/
        """
        serializer = HotelCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        # Create hotel with authenticated user as owner
        hotel = self.hotel_service.create_hotel(
            hotel_data=serializer.validated_data,
            owner_id=request.user.id
        )
        
        # Serialize response
        response_serializer = HotelSerializer(hotel)
        return created_response(response_serializer.data, 'Hotel created successfully')
    
    def list(self, request):
        """
        Lista todos los hoteles con paginación y filtros.
        
        GET /api/hotels/
        
        Query params:
            - page: Número de página (default: 1)
            - page_size: Tamaño de página (default: 20, max: 100)
            - city: Filtrar por ciudad
            - country: Filtrar por país
            - property_type: Filtrar por tipo de propiedad
        """
        # Parse pagination parameters
        pagination = parse_pagination_params(request.query_params)
        
        # Build filters
        filters = {}
        if request.query_params.get('city'):
            filters['address.city'] = request.query_params.get('city')
        if request.query_params.get('country'):
            filters['address.country'] = request.query_params.get('country')
        if request.query_params.get('property_type'):
            filters['property_type'] = request.query_params.get('property_type')
        
        # Fetch hotels and total count
        hotels = self.hotel_service.list_hotels(
            filters=filters,
            skip=pagination['skip'],
            limit=pagination['page_size']
        )
        total = self.hotel_service.count_hotels(filters=filters)
        
        # Serialize and return
        serializer = HotelListSerializer(hotels, many=True)
        
        return success_response(data={
            'count': total,
            'page': pagination['page'],
            'page_size': pagination['page_size'],
            'total_pages': (total + pagination['page_size'] - 1) // pagination['page_size'],
            'results': serializer.data
        })
    
    def retrieve(self, request, pk=None):
        """
        Obtiene el detalle de un hotel específico.
        
        GET /api/hotels/{id}/
        """
        hotel = self.hotel_service.get_hotel_by_id(pk)
        
        if not hotel:
            return not_found_response('Hotel')
        
        serializer = HotelSerializer(hotel)
        return success_response(data=serializer.data)
    
    def update(self, request, pk=None):
        """
        Actualiza un hotel completo (solo propietario).
        
        PUT /api/hotels/{id}/
        """
        serializer = HotelUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        # Update hotel checking ownership
        hotel = self.hotel_service.update_hotel(
            hotel_id=pk,
            update_data=serializer.validated_data,
            owner_id=request.user.id
        )
        
        if not hotel:
            return not_found_response('Hotel')
        
        response_serializer = HotelSerializer(hotel)
        return success_response(data=response_serializer.data)
    
    def partial_update(self, request, pk=None):
        """
        Actualiza parcialmente un hotel (solo propietario).
        
        PATCH /api/hotels/{id}/
        """
        serializer = HotelUpdateSerializer(data=request.data, partial=True)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        # Update hotel checking ownership
        hotel = self.hotel_service.update_hotel(
            hotel_id=pk,
            update_data=serializer.validated_data,
            owner_id=request.user.id
        )
        
        if not hotel:
            return not_found_response('Hotel')
        
        response_serializer = HotelSerializer(hotel)
        return success_response(data=response_serializer.data)
    
    def destroy(self, request, pk=None):
        """
        Elimina un hotel (soft delete, solo propietario).
        
        DELETE /api/hotels/{id}/
        """
        success = self.hotel_service.delete_hotel(
            hotel_id=pk,
            owner_id=request.user.id,
            soft=True
        )
        
        if not success:
            return not_found_response('Hotel')
        
        return success_response(
            message='Hotel deleted successfully',
            status_code=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=['get'], url_path='my-hotels')
    def my_hotels(self, request):
        """
        Obtiene todos los hoteles del usuario autenticado.
        
        GET /api/hotels/my-hotels/
        """
        # Parsear paginación
        pagination = parse_pagination_params(request.query_params)
        
        # Obtener hoteles del usuario
        hotels = self.hotel_service.get_hotels_by_owner(
            owner_id=request.user.id,
            skip=pagination['skip'],
            limit=pagination['page_size']
        )
        
        # Contar total
        total = self.hotel_service.count_hotels(
            filters={'owner_id': str(request.user.id)}
        )
        
        # Serializar
        serializer = HotelListSerializer(hotels, many=True)
        
        return success_response(data={
            'count': total,
            'page': pagination['page'],
            'page_size': pagination['page_size'],
            'total_pages': (total + pagination['page_size'] - 1) // pagination['page_size'],
            'results': serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='add-room')
    def add_room(self, request, pk=None):
        """
        Agrega una habitación al hotel (solo propietario).
        
        POST /api/hotels/{id}/add-room/
        """
        serializer = RoomSerializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        # Agregar habitación
        hotel = self.hotel_service.add_room(
            hotel_id=pk,
            room_data=serializer.validated_data,
            owner_id=request.user.id
        )
        
        if not hotel:
            return not_found_response('Hotel')
        
        response_serializer = HotelSerializer(hotel)
        return created_response(
            data=response_serializer.data,
            message='Habitación agregada exitosamente'
        )
    
    @action(detail=True, methods=['put', 'patch'], url_path='update-room/(?P<room_id>[^/.]+)')
    def update_room(self, request, pk=None, room_id=None):
        """
        Actualiza una habitación específica (solo propietario).
        
        PUT/PATCH /api/hotels/{id}/update-room/{room_id}/
        """
        serializer = RoomSerializer(data=request.data, partial=True)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        # Actualizar habitación
        hotel = self.hotel_service.update_room(
            hotel_id=pk,
            room_id=room_id,
            room_data=serializer.validated_data,
            owner_id=request.user.id
        )
        
        if not hotel:
            return not_found_response('Hotel o habitación')
        
        response_serializer = HotelSerializer(hotel)
        return success_response(
            data=response_serializer.data,
            message='Habitación actualizada exitosamente'
        )
    
    @action(detail=True, methods=['delete'], url_path='delete-room/(?P<room_id>[^/.]+)')
    def delete_room(self, request, pk=None, room_id=None):
        """
        Elimina una habitación específica (solo propietario).
        
        DELETE /api/hotels/{id}/delete-room/{room_id}/
        """
        hotel = self.hotel_service.delete_room(
            hotel_id=pk,
            room_id=room_id,
            owner_id=request.user.id
        )
        
        if not hotel:
            return not_found_response('Hotel o habitación')
        
        response_serializer = HotelSerializer(hotel)
        return success_response(
            data=response_serializer.data,
            message='Habitación eliminada exitosamente'
        )
    
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Búsqueda de texto completo en hoteles.
        
        GET /api/hotels/search/?q=texto
        """
        search_query = request.query_params.get('q', '')
        
        if not search_query:
            return validation_error_response('Parámetro de búsqueda "q" requerido')
        
        # Paginación
        pagination = parse_pagination_params(request.query_params)
        
        # Búsqueda
        hotels = self.hotel_service.search_hotels(
            search_text=search_query,
            skip=pagination['skip'],
            limit=pagination['page_size']
        )
        
        # Serializar
        serializer = HotelListSerializer(hotels, many=True)
        
        return success_response(data={
            'count': len(hotels),
            'page': pagination['page'],
            'page_size': pagination['page_size'],
            'results': serializer.data
        })
