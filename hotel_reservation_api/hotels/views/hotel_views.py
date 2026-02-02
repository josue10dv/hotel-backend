"""
Vistas para la gestión de hoteles.

Implementa endpoints REST usando ViewSets de Django REST Framework.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from hotels.serializers import (
    HotelSerializer,
    HotelListSerializer,
    HotelCreateSerializer,
    HotelUpdateSerializer,
    RoomSerializer,
)
from hotels.services.hotel_service import HotelService
from hotels.utilities import ImageHandler
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
    - GET /api/hotels/                           → Listar todos los hoteles disponibles (público)
    - GET /api/hotels/my-hotels/                 → Listar hoteles del usuario anfitrión (autenticado)
    - GET /api/hotels/{id}/                      → Obtener detalle de hotel (público)
    - PUT /api/hotels/{id}/                      → Actualizar hotel completo (propietario)
    - PATCH /api/hotels/{id}/                    → Actualizar hotel parcial (propietario)
    - DELETE /api/hotels/{id}/                   → Eliminar hotel (propietario)
    - POST /api/hotels/{id}/add-room/            → Agregar habitación (propietario)
    - PUT /api/hotels/{id}/update-room/{room_id}/ → Actualizar habitación (propietario)
    - DELETE /api/hotels/{id}/delete-room/{room_id}/ → Eliminar habitación (propietario)
    - GET /api/hotels/search/                    → Búsqueda de hoteles (público)
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hotel_service = HotelService()
        # Configurar parsers para soportar multipart/form-data
        self.parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_permissions(self):
        """
        Define permisos según la acción.
        
        Acciones públicas: list, retrieve, search
        Acciones autenticadas: my_hotels, create, update, destroy, operaciones de habitaciones
        """
        if self.action in ['list', 'retrieve', 'search']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def create(self, request):
        """
        Crea un nuevo hotel.
        
        POST /api/hotels/
        Acepta multipart/form-data para subir imágenes directamente.
        """
        serializer = HotelCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        hotel_data = serializer.validated_data
        
        # Procesar imágenes si se enviaron archivos
        image_urls = []
        
        # 1. Guardar archivos de imagen si existen
        image_files = request.FILES.getlist('image_files')
        if image_files:
            try:
                uploaded_urls = ImageHandler.save_multiple_images(
                    image_files, 
                    hotel_name=hotel_data.get('name')
                )
                image_urls.extend(uploaded_urls)
            except ValueError as e:
                return validation_error_response({
                    'image_files': [str(e)]
                })
        
        # 2. Agregar URLs proporcionadas directamente
        if 'images' in hotel_data and hotel_data['images']:
            image_urls.extend(hotel_data['images'])
        
        # Actualizar el hotel_data con todas las URLs de imágenes
        hotel_data['images'] = image_urls
        
        # Remover image_files del dict ya que no es parte del schema de MongoDB
        hotel_data.pop('image_files', None)
        
        # Create hotel with authenticated user as owner
        hotel = self.hotel_service.create_hotel(
            hotel_data=hotel_data,
            owner_id=request.user.id
        )
        
        # Serialize response
        response_serializer = HotelSerializer(hotel)
        return created_response(response_serializer.data, 'Hotel created successfully')
    
    def list(self, request):
        """
        Lista todos los hoteles disponibles con paginación y filtros.
        Endpoint público para mostrar todos los hoteles en la plataforma.
        
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
        
        # Build filters - solo hoteles activos
        filters = {
            'is_active': True
        }
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
        Lista todos los hoteles del usuario anfitrión autenticado.
        Muestra solo los hoteles que pertenecen al usuario en sesión.
        
        GET /api/hotels/my-hotels/
        
        Query params:
            - page: Número de página (default: 1)
            - page_size: Tamaño de página (default: 20, max: 100)
            - city: Filtrar por ciudad
            - country: Filtrar por país
            - property_type: Filtrar por tipo de propiedad
            - is_active: Filtrar por estado activo/inactivo (true/false)
        """
        # Parsear paginación
        pagination = parse_pagination_params(request.query_params)
        
        # Build filters - incluir owner_id del usuario autenticado
        filters = {
            'owner_id': str(request.user.id)
        }
        
        # Filtros opcionales
        if request.query_params.get('city'):
            filters['address.city'] = request.query_params.get('city')
        if request.query_params.get('country'):
            filters['address.country'] = request.query_params.get('country')
        if request.query_params.get('property_type'):
            filters['property_type'] = request.query_params.get('property_type')
        if request.query_params.get('is_active'):
            is_active = request.query_params.get('is_active').lower() == 'true'
            filters['is_active'] = is_active
        
        # Obtener hoteles del usuario con filtros
        hotels = self.hotel_service.list_hotels(
            filters=filters,
            skip=pagination['skip'],
            limit=pagination['page_size']
        )
        
        # Contar total
        total = self.hotel_service.count_hotels(filters=filters)
        
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
    
    @action(detail=False, methods=['get'], url_path='advanced-search')
    def advanced_search(self, request):
        """
        Búsqueda avanzada con filtros múltiples.
        
        GET /api/hotels/advanced-search/?city=Montevideo&min_price=50&max_price=200&amenities=WiFi,Pool
        
        Query Parameters:
            - q: Término de búsqueda general
            - city, country, property_type
            - min_price, max_price: Rango de precios por noche
            - min_rating: Rating mínimo (1-5)
            - amenities: Lista separada por comas
            - guests: Número de huéspedes
            - check_in, check_out: Fechas ISO 8601
            - sort_by: price_asc, price_desc, rating, popular
        """
        from datetime import datetime
        
        # Pagination
        pagination = parse_pagination_params(request.query_params)
        
        # Build filters
        filters = {'is_active': True}
        
        # Location filters
        if request.query_params.get('city'):
            filters['address.city'] = request.query_params.get('city')
        if request.query_params.get('country'):
            filters['address.country'] = request.query_params.get('country')
        if request.query_params.get('property_type'):
            filters['property_type'] = request.query_params.get('property_type')
        
        # Price range
        price_filter = {}
        if request.query_params.get('min_price'):
            try:
                price_filter['$gte'] = float(request.query_params.get('min_price'))
            except ValueError:
                pass
        if request.query_params.get('max_price'):
            try:
                price_filter['$lte'] = float(request.query_params.get('max_price'))
            except ValueError:
                pass
        
        # Rating filter
        if request.query_params.get('min_rating'):
            try:
                filters['rating'] = {'$gte': float(request.query_params.get('min_rating'))}
            except ValueError:
                pass
        
        # Amenities filter
        if request.query_params.get('amenities'):
            amenities_list = [a.strip() for a in request.query_params.get('amenities').split(',')]
            filters['amenities'] = {'$all': amenities_list}
        
        # Search query
        search_query = request.query_params.get('q', '')
        
        # Fetch hotels
        hotels = self.hotel_service.list_hotels(
            filters=filters,
            skip=pagination['skip'],
            limit=pagination['page_size']
        )
        
        # Apply price filter if needed (filter rooms)
        if price_filter:
            filtered_hotels = []
            for hotel in hotels:
                if hotel.get('rooms'):
                    min_room_price = min([room.get('price_per_night', float('inf')) for room in hotel['rooms']])
                    if price_filter.get('$gte', 0) <= min_room_price <= price_filter.get('$lte', float('inf')):
                        filtered_hotels.append(hotel)
                elif not price_filter:
                    filtered_hotels.append(hotel)
            hotels = filtered_hotels
        
        # Sort
        sort_by = request.query_params.get('sort_by', 'popular')
        if sort_by == 'price_asc' and hotels:
            hotels = sorted(hotels, key=lambda h: min([r.get('price_per_night', 0) for r in h.get('rooms', [])], default=0))
        elif sort_by == 'price_desc' and hotels:
            hotels = sorted(hotels, key=lambda h: min([r.get('price_per_night', 0) for r in h.get('rooms', [])], default=0), reverse=True)
        elif sort_by == 'rating':
            hotels = sorted(hotels, key=lambda h: h.get('rating', 0), reverse=True)
        
        # Count
        total = self.hotel_service.count_hotels(filters=filters)
        
        # Serialize
        serializer = HotelListSerializer(hotels, many=True)
        
        return success_response(data={
            'count': total,
            'page': pagination['page'],
            'page_size': pagination['page_size'],
            'total_pages': (total + pagination['page_size'] - 1) // pagination['page_size'],
            'filters_applied': {
                'city': request.query_params.get('city'),
                'country': request.query_params.get('country'),
                'property_type': request.query_params.get('property_type'),
                'min_price': request.query_params.get('min_price'),
                'max_price': request.query_params.get('max_price'),
                'min_rating': request.query_params.get('min_rating'),
                'amenities': request.query_params.get('amenities'),
            },
            'results': serializer.data
        })
    
    @action(detail=True, methods=['get'], url_path='availability')
    def availability(self, request, pk=None):
        """
        Obtiene la disponibilidad de un hotel en un rango de fechas.
        
        GET /api/hotels/{id}/availability/?start_date=2026-03-01&end_date=2026-03-10
        
        Query Parameters:
            - start_date: Fecha inicio (ISO 8601) - Requerido
            - end_date: Fecha fin (ISO 8601) - Requerido
            - room_type: Filtrar por tipo de habitación (opcional)
        """
        from datetime import datetime, timedelta
        from reservations.services.reservation_service import ReservationService
        
        # Validate dates
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        
        if not start_date_str or not end_date_str:
            return validation_error_response({
                'dates': ['start_date and end_date are required']
            })
        
        try:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        except ValueError:
            return validation_error_response({
                'dates': ['Invalid date format. Use ISO 8601 format']
            })
        
        if start_date >= end_date:
            return validation_error_response({
                'dates': ['end_date must be after start_date']
            })
        
        # Get hotel
        hotel = self.hotel_service.get_hotel_by_id(pk)
        if not hotel:
            return not_found_response('Hotel')
        
        # Get reservations for this hotel in date range
        reservation_service = ReservationService()
        
        # Build availability calendar
        availability = []
        current_date = start_date.date()
        end = end_date.date()
        
        while current_date <= end:
            day_availability = {
                'date': current_date.isoformat(),
                'rooms': []
            }
            
            for room in hotel.get('rooms', []):
                room_type = request.query_params.get('room_type')
                if room_type and room.get('type') != room_type:
                    continue
                
                # Check if room is available on this date
                is_available = room.get('available', True)
                
                day_availability['rooms'].append({
                    'room_id': room.get('room_id'),
                    'name': room.get('name'),
                    'type': room.get('type'),
                    'available': is_available,
                    'price': float(room.get('price_per_night', 0))
                })
            
            availability.append(day_availability)
            current_date += timedelta(days=1)
        
        return success_response(data={
            'hotel_id': str(hotel.get('_id')),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'availability': availability
        })
