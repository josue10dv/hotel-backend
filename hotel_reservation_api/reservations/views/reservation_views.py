"""
Views para la gestión de reservaciones.
Implementa endpoints REST usando ViewSets de Django REST Framework.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from reservations.serializers import (
    ReservationCreateSerializer,
    ReservationListSerializer,
    ReservationDetailSerializer,
    ReservationUpdateSerializer,
    CheckAvailabilitySerializer
)
from reservations.services.reservation_service import ReservationService
from datetime import datetime


class ReservationViewSet(viewsets.ViewSet):
    """
    ViewSet para operaciones de reservaciones.
    
    Endpoints disponibles:
    
    Para huéspedes (guests):
    - POST /api/reservations/                      → Crear nueva reservación
    - GET /api/reservations/                       → Listar reservaciones del usuario
    - GET /api/reservations/{id}/                  → Ver detalle de una reservación
    - PATCH /api/reservations/{id}/cancel/         → Cancelar reservación
    - GET /api/reservations/check-availability/    → Verificar disponibilidad
    
    Para propietarios (owners):
    - GET /api/reservations/my-properties/         → Ver reservaciones de sus hoteles
    - PATCH /api/reservations/{id}/confirm/        → Confirmar reservación
    - PATCH /api/reservations/{id}/reject/         → Rechazar reservación
    - PATCH /api/reservations/{id}/complete/       → Marcar como completada
    - GET /api/reservations/calendar/              → Vista calendario de reservaciones
    """
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.reservation_service = ReservationService()
    
    def create(self, request):
        """
        Crea una nueva reservación.
        Solo usuarios tipo 'guest' pueden crear reservaciones.
        
        POST /api/reservations/
        """
        # Validar que el usuario sea tipo guest
        if not hasattr(request.user, 'user_type') or request.user.user_type != 'guest':
            return Response(
                {'error': 'Solo los huéspedes pueden crear reservaciones'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ReservationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            reservation = self.reservation_service.create_reservation(
                serializer.validated_data,
                request.user.id
            )
            return Response(
                {
                    'message': 'Reservación creada exitosamente',
                    'data': reservation
                },
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error al crear la reservación: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def list(self, request):
        """
        Lista todas las reservaciones del usuario autenticado (huésped).
        
        GET /api/reservations/
        Query params opcionales: status, from_date, to_date
        """
        # Obtener filtros de query params
        filters = {}
        if request.query_params.get('status'):
            filters['status'] = request.query_params.get('status')
        if request.query_params.get('from_date'):
            try:
                filters['from_date'] = datetime.fromisoformat(
                    request.query_params.get('from_date')
                )
            except ValueError:
                return Response(
                    {'error': 'Formato de from_date inválido. Use ISO 8601.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        if request.query_params.get('to_date'):
            try:
                filters['to_date'] = datetime.fromisoformat(
                    request.query_params.get('to_date')
                )
            except ValueError:
                return Response(
                    {'error': 'Formato de to_date inválido. Use ISO 8601.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            reservations = self.reservation_service.get_reservations_by_guest(
                str(request.user.id),
                filters
            )
            serializer = ReservationListSerializer(reservations, many=True)
            return Response(
                {
                    'count': len(reservations),
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Error al obtener reservaciones: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, pk=None):
        """
        Obtiene el detalle de una reservación específica.
        
        GET /api/reservations/{id}/
        """
        try:
            reservation = self.reservation_service.get_reservation_by_id(pk)
            if not reservation:
                return Response(
                    {'error': 'Reservación no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verificar que el usuario tenga permiso para ver esta reservación
            user_id = str(request.user.id)
            if (reservation['guest_id'] != user_id and 
                reservation['owner_id'] != user_id):
                return Response(
                    {'error': 'No tienes permiso para ver esta reservación'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = ReservationDetailSerializer(reservation)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'Error al obtener la reservación: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        Cancela una reservación (solo huésped).
        
        PATCH /api/reservations/{id}/cancel/
        Body: { "cancellation_reason": "..." }
        """
        cancellation_reason = request.data.get('cancellation_reason', '')
        
        if not cancellation_reason:
            return Response(
                {'error': 'Debe proporcionar una razón de cancelación'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            reservation = self.reservation_service.update_reservation_status(
                pk,
                'cancelled',
                str(request.user.id),
                'guest',
                cancellation_reason
            )
            return Response(
                {
                    'message': 'Reservación cancelada exitosamente',
                    'data': reservation
                },
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error al cancelar la reservación: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='my-properties')
    def my_properties(self, request):
        """
        Lista reservaciones de los hoteles del propietario.
        
        GET /api/reservations/my-properties/
        Query params opcionales: status, hotel_id, from_date, to_date
        """
        # Validar que el usuario sea propietario
        if not hasattr(request.user, 'user_type') or request.user.user_type != 'owner':
            return Response(
                {'error': 'Solo los propietarios pueden acceder a esta información'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Obtener filtros de query params
        filters = {}
        if request.query_params.get('status'):
            filters['status'] = request.query_params.get('status')
        if request.query_params.get('hotel_id'):
            filters['hotel_id'] = request.query_params.get('hotel_id')
        if request.query_params.get('from_date'):
            try:
                filters['from_date'] = datetime.fromisoformat(
                    request.query_params.get('from_date')
                )
            except ValueError:
                return Response(
                    {'error': 'Formato de from_date inválido. Use ISO 8601.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        if request.query_params.get('to_date'):
            try:
                filters['to_date'] = datetime.fromisoformat(
                    request.query_params.get('to_date')
                )
            except ValueError:
                return Response(
                    {'error': 'Formato de to_date inválido. Use ISO 8601.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            reservations = self.reservation_service.get_reservations_by_owner(
                str(request.user.id),
                filters
            )
            serializer = ReservationListSerializer(reservations, many=True)
            return Response(
                {
                    'count': len(reservations),
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Error al obtener reservaciones: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'], url_path='confirm')
    def confirm(self, request, pk=None):
        """
        Confirma una reservación (solo propietario).
        
        PATCH /api/reservations/{id}/confirm/
        """
        # Validar que el usuario sea propietario
        if not hasattr(request.user, 'user_type') or request.user.user_type != 'owner':
            return Response(
                {'error': 'Solo los propietarios pueden confirmar reservaciones'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            reservation = self.reservation_service.update_reservation_status(
                pk,
                'confirmed',
                str(request.user.id),
                'owner'
            )
            return Response(
                {
                    'message': 'Reservación confirmada exitosamente',
                    'data': reservation
                },
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error al confirmar la reservación: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'], url_path='reject')
    def reject(self, request, pk=None):
        """
        Rechaza una reservación (solo propietario).
        
        PATCH /api/reservations/{id}/reject/
        """
        # Validar que el usuario sea propietario
        if not hasattr(request.user, 'user_type') or request.user.user_type != 'owner':
            return Response(
                {'error': 'Solo los propietarios pueden rechazar reservaciones'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            reservation = self.reservation_service.update_reservation_status(
                pk,
                'rejected',
                str(request.user.id),
                'owner'
            )
            return Response(
                {
                    'message': 'Reservación rechazada exitosamente',
                    'data': reservation
                },
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error al rechazar la reservación: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'], url_path='complete')
    def complete(self, request, pk=None):
        """
        Marca una reservación como completada (solo propietario).
        
        PATCH /api/reservations/{id}/complete/
        """
        # Validar que el usuario sea propietario
        if not hasattr(request.user, 'user_type') or request.user.user_type != 'owner':
            return Response(
                {'error': 'Solo los propietarios pueden completar reservaciones'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            reservation = self.reservation_service.update_reservation_status(
                pk,
                'completed',
                str(request.user.id),
                'owner'
            )
            return Response(
                {
                    'message': 'Reservación marcada como completada',
                    'data': reservation
                },
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error al completar la reservación: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='check-availability')
    def check_availability(self, request):
        """
        Verifica la disponibilidad de una habitación sin crear una reservación.
        
        GET /api/reservations/check-availability/
        Query params: hotel_id, room_id, check_in, check_out
        """
        serializer = CheckAvailabilitySerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            is_available = self.reservation_service.check_availability(
                serializer.validated_data['hotel_id'],
                serializer.validated_data['room_id'],
                serializer.validated_data['check_in'],
                serializer.validated_data['check_out']
            )
            
            return Response(
                {
                    'available': is_available,
                    'message': 'La habitación está disponible' if is_available 
                              else 'La habitación no está disponible en las fechas seleccionadas'
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Error al verificar disponibilidad: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='calendar')
    def calendar(self, request):
        """
        Obtiene las reservaciones de un hotel para un mes específico (vista calendario).
        
        GET /api/reservations/calendar/
        Query params: hotel_id, year, month
        """
        # Validar que el usuario sea propietario
        if not hasattr(request.user, 'user_type') or request.user.user_type != 'owner':
            return Response(
                {'error': 'Solo los propietarios pueden acceder al calendario'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        hotel_id = request.query_params.get('hotel_id')
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        
        if not all([hotel_id, year, month]):
            return Response(
                {'error': 'Se requieren los parámetros: hotel_id, year, month'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            year = int(year)
            month = int(month)
            
            if month < 1 or month > 12:
                return Response(
                    {'error': 'El mes debe estar entre 1 y 12'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            reservations = self.reservation_service.get_calendar_reservations(
                hotel_id, year, month
            )
            serializer = ReservationListSerializer(reservations, many=True)
            
            return Response(
                {
                    'hotel_id': hotel_id,
                    'year': year,
                    'month': month,
                    'count': len(reservations),
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except ValueError:
            return Response(
                {'error': 'Formato de year o month inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error al obtener el calendario: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
