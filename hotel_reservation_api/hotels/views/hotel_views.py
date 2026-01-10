"""
Views para la gestión de hoteles.
Implementa endpoints REST usando ViewSets de Django REST Framework.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from hotels.serializers import (
    HotelSerializer,
    HotelListSerializer,
    HotelCreateSerializer,
    HotelUpdateSerializer,
    RoomSerializer,
)
from hotels.services.hotel_service import HotelService


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
        - list, retrieve, search: Público (AllowAny)
        - create, update, partial_update, destroy, my_hotels, room operations: Autenticado
        """
        if self.action in ['list', 'retrieve', 'search']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def create(self, request):
        """
        POST /api/hotels/
        Crear un nuevo hotel.
        """
        serializer = HotelCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear hotel con el ID del usuario autenticado como propietario
        hotel = self.hotel_service.create_hotel(
            hotel_data=serializer.validated_data,
            owner_id=request.user.id
        )
        
        # Serializar respuesta
        response_serializer = HotelSerializer(hotel)
        
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def list(self, request):
        """
        GET /api/hotels/
        Listar todos los hoteles con paginación.
        
        Query params:
        - page: Número de página (default: 1)
        - page_size: Tamaño de página (default: 20, max: 100)
        - city: Filtrar por ciudad
        - country: Filtrar por país
        - property_type: Filtrar por tipo de propiedad
        """
        # Paginación
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        skip = (page - 1) * page_size
        
        # Filtros
        filters = {}
        
        if request.query_params.get('city'):
            filters['address.city'] = request.query_params.get('city')
        
        if request.query_params.get('country'):
            filters['address.country'] = request.query_params.get('country')
        
        if request.query_params.get('property_type'):
            filters['property_type'] = request.query_params.get('property_type')
        
        # Obtener hoteles y total
        hotels = self.hotel_service.list_hotels(
            filters=filters,
            skip=skip,
            limit=page_size
        )
        total = self.hotel_service.count_hotels(filters=filters)
        
        # Serializar
        serializer = HotelListSerializer(hotels, many=True)
        
        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
            'results': serializer.data
        })
    
    def retrieve(self, request, pk=None):
        """
        GET /api/hotels/{id}/
        Obtener detalle de un hotel específico.
        """
        hotel = self.hotel_service.get_hotel_by_id(pk)
        
        if not hotel:
            return Response(
                {'detail': 'Hotel no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = HotelSerializer(hotel)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """
        PUT /api/hotels/{id}/
        Actualizar un hotel completo (solo propietario).
        """
        serializer = HotelUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar hotel verificando que sea el propietario
        hotel = self.hotel_service.update_hotel(
            hotel_id=pk,
            update_data=serializer.validated_data,
            owner_id=request.user.id
        )
        
        if not hotel:
            return Response(
                {'detail': 'Hotel no encontrado o no tienes permisos'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        response_serializer = HotelSerializer(hotel)
        return Response(response_serializer.data)
    
    def partial_update(self, request, pk=None):
        """
        PATCH /api/hotels/{id}/
        Actualizar parcialmente un hotel (solo propietario).
        """
        serializer = HotelUpdateSerializer(data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar hotel verificando que sea el propietario
        hotel = self.hotel_service.update_hotel(
            hotel_id=pk,
            update_data=serializer.validated_data,
            owner_id=request.user.id
        )
        
        if not hotel:
            return Response(
                {'detail': 'Hotel no encontrado o no tienes permisos'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        response_serializer = HotelSerializer(hotel)
        return Response(response_serializer.data)
    
    def destroy(self, request, pk=None):
        """
        DELETE /api/hotels/{id}/
        Eliminar un hotel (soft delete, solo propietario).
        """
        success = self.hotel_service.delete_hotel(
            hotel_id=pk,
            owner_id=request.user.id,
            soft=True
        )
        
        if not success:
            return Response(
                {'detail': 'Hotel no encontrado o no tienes permisos'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(
            {'detail': 'Hotel eliminado correctamente'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=['get'], url_path='my-hotels')
    def my_hotels(self, request):
        """
        GET /api/hotels/my-hotels/
        Obtener todos los hoteles del usuario autenticado.
        """
        # Paginación
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        skip = (page - 1) * page_size
        
        # Obtener hoteles del usuario
        hotels = self.hotel_service.get_hotels_by_owner(
            owner_id=request.user.id,
            skip=skip,
            limit=page_size
        )
        
        # Contar total
        total = self.hotel_service.count_hotels(
            filters={'owner_id': str(request.user.id)}
        )
        
        # Serializar
        serializer = HotelListSerializer(hotels, many=True)
        
        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size,
            'results': serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='add-room')
    def add_room(self, request, pk=None):
        """
        POST /api/hotels/{id}/add-room/
        Agregar una habitación al hotel (solo propietario).
        """
        serializer = RoomSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Agregar habitación
        hotel = self.hotel_service.add_room(
            hotel_id=pk,
            room_data=serializer.validated_data,
            owner_id=request.user.id
        )
        
        if not hotel:
            return Response(
                {'detail': 'Hotel no encontrado o no tienes permisos'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        response_serializer = HotelSerializer(hotel)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['put', 'patch'], url_path='update-room/(?P<room_id>[^/.]+)')
    def update_room(self, request, pk=None, room_id=None):
        """
        PUT/PATCH /api/hotels/{id}/update-room/{room_id}/
        Actualizar una habitación específica (solo propietario).
        """
        serializer = RoomSerializer(data=request.data, partial=True)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar habitación
        hotel = self.hotel_service.update_room(
            hotel_id=pk,
            room_id=room_id,
            room_data=serializer.validated_data,
            owner_id=request.user.id
        )
        
        if not hotel:
            return Response(
                {'detail': 'Hotel o habitación no encontrado, o no tienes permisos'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        response_serializer = HotelSerializer(hotel)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['delete'], url_path='delete-room/(?P<room_id>[^/.]+)')
    def delete_room(self, request, pk=None, room_id=None):
        """
        DELETE /api/hotels/{id}/delete-room/{room_id}/
        Eliminar una habitación específica (solo propietario).
        """
        hotel = self.hotel_service.delete_room(
            hotel_id=pk,
            room_id=room_id,
            owner_id=request.user.id
        )
        
        if not hotel:
            return Response(
                {'detail': 'Hotel o habitación no encontrado, o no tienes permisos'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        response_serializer = HotelSerializer(hotel)
        return Response(response_serializer.data)
    
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        GET /api/hotels/search/?q=texto
        Búsqueda de texto completo en hoteles.
        """
        search_query = request.query_params.get('q', '')
        
        if not search_query:
            return Response(
                {'detail': 'Parámetro de búsqueda "q" requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Paginación
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 20)), 100)
        skip = (page - 1) * page_size
        
        # Búsqueda
        hotels = self.hotel_service.search_hotels(
            search_text=search_query,
            skip=skip,
            limit=page_size
        )
        
        # Serializar
        serializer = HotelListSerializer(hotels, many=True)
        
        return Response({
            'count': len(hotels),
            'page': page,
            'page_size': page_size,
            'results': serializer.data
        })
