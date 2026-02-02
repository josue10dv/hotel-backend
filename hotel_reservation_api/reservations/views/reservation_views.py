"""
Vistas para la gestión de reservaciones.

Implementa endpoints REST usando ViewSets de Django REST Framework.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from reservations.serializers import (
    ReservationCreateSerializer,
    ReservationListSerializer,
    ReservationDetailSerializer,
    ReservationUpdateSerializer,
    CheckAvailabilitySerializer
)
from reservations.services.reservation_service import ReservationService
from app.utilities import (
    created_response,
    success_response,
    error_response,
    validation_error_response,
    permission_denied_response,
    not_found_response,
    parse_datetime_param,
    check_user_type,
)


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
        # Validate user type using utility
        permission_error = check_user_type(
            request.user, 
            'guest', 
            'Only guests can create reservations'
        )
        if permission_error:
            return permission_error
        
        serializer = ReservationCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        try:
            reservation = self.reservation_service.create_reservation(
                serializer.validated_data,
                request.user.id
            )
            return created_response(
                data=reservation,
                message='Reservation created successfully'
            )
        except ValueError as e:
            return error_response(str(e))
        except Exception as e:
            return error_response(
                f'Error creating reservation: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def list(self, request):
        """
        Lista todas las reservaciones del usuario autenticado (huésped).
        
        GET /api/reservations/
        Query params opcionales: status, from_date, to_date
        """
        # Build filters from query params
        filters = {}
        
        if request.query_params.get('status'):
            filters['status'] = request.query_params.get('status')
        
        # Parse date parameters using utility
        from_date, error = parse_datetime_param(request.query_params.get('from_date'), 'from_date')
        if error:
            return error
        if from_date:
            filters['from_date'] = from_date
        
        to_date, error = parse_datetime_param(request.query_params.get('to_date'), 'to_date')
        if error:
            return error
        if to_date:
            filters['to_date'] = to_date
        
        try:
            reservations = self.reservation_service.get_reservations_by_guest(
                str(request.user.id),
                filters
            )
            serializer = ReservationListSerializer(reservations, many=True)
            return success_response(data={
                'count': len(reservations),
                'reservations': serializer.data
            })
        except Exception as e:
            return error_response(
                f'Error retrieving reservations: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, pk=None):
        """
        Obtiene el detalle de una reservación específica.
        
        GET /api/reservations/{id}/
        """
        try:
            reservation = self.reservation_service.get_reservation_by_id(pk)
            
            if not reservation:
                return not_found_response('Reservation')
            
            # Verify user has permission to view this reservation
            user_id = str(request.user.id)
            if (reservation['guest_id'] != user_id and 
                reservation['owner_id'] != user_id):
                return permission_denied_response(
                    'You do not have permission to view this reservation'
                )
            
            serializer = ReservationDetailSerializer(reservation)
            return success_response(data=serializer.data)
        except Exception as e:
            return error_response(
                f'Error retrieving reservation: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
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
            return error_response('Debe proporcionar una razón de cancelación')
        
        try:
            reservation = self.reservation_service.update_reservation_status(
                pk,
                'cancelled',
                str(request.user.id),
                'guest',
                cancellation_reason
            )
            return success_response(
                data=reservation,
                message='Reservación cancelada exitosamente'
            )
        except ValueError as e:
            return error_response(str(e))
        except Exception as e:
            return error_response(
                f'Error al cancelar la reservación: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='my-properties')
    def my_properties(self, request):
        """
        Lista reservaciones de los hoteles del propietario.
        
        GET /api/reservations/my-properties/
        Query params opcionales: status, hotel_id, from_date, to_date
        """
        # Validar que el usuario sea propietario
        permission_error = check_user_type(
            request.user,
            'owner',
            'Solo los propietarios pueden acceder a esta información'
        )
        if permission_error:
            return permission_error
        
        # Construir filtros
        filters = {}
        if request.query_params.get('status'):
            filters['status'] = request.query_params.get('status')
        if request.query_params.get('hotel_id'):
            filters['hotel_id'] = request.query_params.get('hotel_id')
        
        # Parsear fechas
        from_date, error = parse_datetime_param(request.query_params.get('from_date'), 'from_date')
        if error:
            return error
        if from_date:
            filters['from_date'] = from_date
        
        to_date, error = parse_datetime_param(request.query_params.get('to_date'), 'to_date')
        if error:
            return error
        if to_date:
            filters['to_date'] = to_date
        
        try:
            reservations = self.reservation_service.get_reservations_by_owner(
                str(request.user.id),
                filters
            )
            serializer = ReservationListSerializer(reservations, many=True)
            return success_response(data={
                'count': len(reservations),
                'reservations': serializer.data
            })
        except Exception as e:
            return error_response(
                f'Error al obtener reservaciones: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'], url_path='confirm')
    def confirm(self, request, pk=None):
        """
        Confirma una reservación (solo propietario).
        
        PATCH /api/reservations/{id}/confirm/
        """
        # Validar que el usuario sea propietario
        permission_error = check_user_type(
            request.user,
            'owner',
            'Solo los propietarios pueden confirmar reservaciones'
        )
        if permission_error:
            return permission_error
        
        try:
            reservation = self.reservation_service.update_reservation_status(
                pk,
                'confirmed',
                str(request.user.id),
                'owner'
            )
            return success_response(
                data=reservation,
                message='Reservación confirmada exitosamente'
            )
        except ValueError as e:
            return error_response(str(e))
        except Exception as e:
            return error_response(
                f'Error al confirmar la reservación: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'], url_path='reject')
    def reject(self, request, pk=None):
        """
        Rechaza una reservación (solo propietario).
        
        PATCH /api/reservations/{id}/reject/
        """
        # Validar que el usuario sea propietario
        permission_error = check_user_type(
            request.user,
            'owner',
            'Solo los propietarios pueden rechazar reservaciones'
        )
        if permission_error:
            return permission_error
        
        try:
            reservation = self.reservation_service.update_reservation_status(
                pk,
                'rejected',
                str(request.user.id),
                'owner'
            )
            return success_response(
                data=reservation,
                message='Reservación rechazada exitosamente'
            )
        except ValueError as e:
            return error_response(str(e))
        except Exception as e:
            return error_response(
                f'Error al rechazar la reservación: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['patch'], url_path='complete')
    def complete(self, request, pk=None):
        """
        Marca una reservación como completada (solo propietario).
        
        PATCH /api/reservations/{id}/complete/
        """
        # Validar que el usuario sea propietario
        permission_error = check_user_type(
            request.user,
            'owner',
            'Solo los propietarios pueden completar reservaciones'
        )
        if permission_error:
            return permission_error
        
        try:
            reservation = self.reservation_service.update_reservation_status(
                pk,
                'completed',
                str(request.user.id),
                'owner'
            )
            return success_response(
                data=reservation,
                message='Reservación marcada como completada'
            )
        except ValueError as e:
            return error_response(str(e))
        except Exception as e:
            return error_response(
                f'Error al completar la reservación: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
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
            return validation_error_response(serializer.errors)
        
        try:
            is_available = self.reservation_service.check_availability(
                serializer.validated_data['hotel_id'],
                serializer.validated_data['room_id'],
                serializer.validated_data['check_in'],
                serializer.validated_data['check_out']
            )
            
            return success_response(
                data={'available': is_available},
                message='La habitación está disponible' if is_available 
                        else 'La habitación no está disponible en las fechas seleccionadas'
            )
        except Exception as e:
            return error_response(
                f'Error al verificar disponibilidad: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='calendar')
    def calendar(self, request):
        """
        Obtiene las reservaciones de un hotel para un mes específico (vista calendario).
        
        GET /api/reservations/calendar/
        Query params: hotel_id, year, month
        """
        # Validar que el usuario sea propietario
        permission_error = check_user_type(
            request.user,
            'owner',
            'Solo los propietarios pueden acceder al calendario'
        )
        if permission_error:
            return permission_error
        
        hotel_id = request.query_params.get('hotel_id')
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        
        if not all([hotel_id, year, month]):
            return error_response('Se requieren los parámetros: hotel_id, year, month')
        
        try:
            year = int(year)
            month = int(month)
            
            if month < 1 or month > 12:
                return error_response('El mes debe estar entre 1 y 12')
            
            reservations = self.reservation_service.get_calendar_reservations(
                hotel_id, year, month
            )
            serializer = ReservationListSerializer(reservations, many=True)
            
            return success_response(data={
                'hotel_id': hotel_id,
                'year': year,
                'month': month,
                'count': len(reservations),
                'reservations': serializer.data
            })
        except ValueError:
            return error_response('Formato de year o month inválido')
        except Exception as e:
            return error_response(
                f'Error al obtener el calendario: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
