"""
Vistas para la gestión de pagos.

Implementa endpoints REST usando ViewSets de Django REST Framework.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from payments.models import Payment, Transaction
from payments.serializers import (
    PaymentCreateSerializer,
    PaymentListSerializer,
    PaymentDetailSerializer,
    PaymentRefundSerializer,
    TransactionSerializer,
    PaymentStatisticsSerializer
)
from payments.services.payment_service import PaymentService
from app.utilities import (
    created_response,
    success_response,
    error_response,
    validation_error_response,
    permission_denied_response,
    parse_datetime_param,
    check_user_type,
)


class PaymentViewSet(viewsets.ViewSet):
    """
    ViewSet para operaciones de pagos.
    
    Endpoints disponibles:
    
    Para todos los usuarios autenticados:
    - POST /api/payments/                      → Crear y procesar pago
    - GET /api/payments/                       → Listar mis pagos
    - GET /api/payments/{id}/                  → Ver detalle de un pago
    - POST /api/payments/{id}/verify/          → Verificar estado del pago
    - GET /api/payments/{id}/transactions/     → Ver transacciones del pago
    - GET /api/payments/statistics/            → Estadísticas de mis pagos
    
    Para propietarios (owners):
    - GET /api/payments/my-earnings/           → Ver ganancias
    - POST /api/payments/{id}/refund/          → Procesar reembolso
    """
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.payment_service = PaymentService()
    
    def create(self, request):
        """
        Crea y procesa un nuevo pago.
        
        POST /api/payments/
        Body: {
            "reservation_id": "uuid",
            "payment_method": "credit_card",
            "payment_gateway": "stripe",
            "payment_token": "tok_xxx",
            "save_payment_method": false,
            "metadata": {}
        }
        """
        serializer = PaymentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        try:
            # Crear el registro de pago
            payment = self.payment_service.create_payment(
                serializer.validated_data,
                request.user
            )
            
            # Obtener token de pago
            payment_token = serializer.validated_data.get('payment_token')
            
            if not payment_token:
                # Si no hay token, solo crear el registro en estado pending
                detail_serializer = PaymentDetailSerializer(payment)
                return created_response(
                    data=detail_serializer.data,
                    message='Pago creado en estado pendiente'
                )
            
            # Procesar el pago con la pasarela
            result = self.payment_service.process_payment(payment, payment_token)
            
            if result['success']:
                detail_serializer = PaymentDetailSerializer(result['payment'])
                return created_response(
                    data=detail_serializer.data,
                    message=result['message']
                )
            else:
                detail_serializer = PaymentDetailSerializer(result['payment'])
                return error_response(
                    error=result['error'],
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    error_code=result.get('error_code'),
                    additional_data={'data': detail_serializer.data}
                )
        
        except ValueError as e:
            return error_response(str(e))
        except Exception as e:
            return error_response(
                f'Error al procesar el pago: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def list(self, request):
        """
        Lista todos los pagos del usuario autenticado.
        
        GET /api/payments/
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
            payments = self.payment_service.get_user_payments(
                request.user,
                filters
            )
            serializer = PaymentListSerializer(payments, many=True)
            return success_response(data={
                'count': payments.count(),
                'payments': serializer.data
            })
        except Exception as e:
            return error_response(
                f'Error retrieving payments: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, pk=None):
        """
        Obtiene el detalle de un pago específico.
        
        GET /api/payments/{id}/
        """
        try:
            payment = get_object_or_404(Payment, pk=pk)
            
            # Verificar permisos
            if payment.user != request.user:
                # Si no es el dueño, verificar si es el propietario de la reservación
                reservation = self.payment_service._get_reservation(payment.reservation_id)
                if not reservation or str(reservation['owner_id']) != str(request.user.id):
                    return permission_denied_response('No tienes permiso para ver este pago')
            
            serializer = PaymentDetailSerializer(payment)
            return success_response(data=serializer.data)
        except Exception as e:
            return error_response(
                f'Error al obtener el pago: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='verify')
    def verify(self, request, pk=None):
        """
        Verifica el estado de un pago con la pasarela.
        
        POST /api/payments/{id}/verify/
        """
        try:
            payment = get_object_or_404(Payment, pk=pk)
            
            # Verificar permisos
            if payment.user != request.user:
                return permission_denied_response('No tienes permiso para verificar este pago')
            
            result = self.payment_service.verify_payment(payment)
            
            if result['success']:
                serializer = PaymentDetailSerializer(result['payment'])
                return success_response(
                    data={
                        'gateway_status': result.get('status'),
                        'payment': serializer.data
                    },
                    message='Estado del pago verificado'
                )
            else:
                return error_response(result.get('error', 'Error al verificar el pago'))
        except ValueError as e:
            return error_response(str(e))
        except Exception as e:
            return error_response(
                f'Error al verificar el pago: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='transactions')
    def transactions(self, request, pk=None):
        """
        Lista todas las transacciones de un pago.
        
        GET /api/payments/{id}/transactions/
        """
        try:
            payment = get_object_or_404(Payment, pk=pk)
            
            # Verificar permisos
            if payment.user != request.user:
                reservation = self.payment_service._get_reservation(payment.reservation_id)
                if not reservation or str(reservation['owner_id']) != str(request.user.id):
                    return permission_denied_response('No tienes permiso para ver las transacciones')
            
            transactions = payment.transactions.all().order_by('-created_at')
            serializer = TransactionSerializer(transactions, many=True)
            
            return success_response(data={
                'count': transactions.count(),
                'transactions': serializer.data
            })
        except Exception as e:
            return error_response(
                f'Error al obtener transacciones: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='refund')
    def refund(self, request, pk=None):
        """
        Procesa un reembolso (solo propietarios).
        
        POST /api/payments/{id}/refund/
        Body: {
            "amount": 100.00,  # opcional, si no se envía se reembolsa todo
            "reason": "Razón del reembolso"
        }
        """
        # Validar que el usuario sea propietario
        permission_error = check_user_type(
            request.user, 
            'owner', 
            'Solo los propietarios pueden procesar reembolsos'
        )
        if permission_error:
            return permission_error
        
        try:
            payment = get_object_or_404(Payment, pk=pk)
            
            # Verificar que el propietario sea dueño de la reservación
            reservation = self.payment_service._get_reservation(payment.reservation_id)
            if not reservation or str(reservation['owner_id']) != str(request.user.id):
                return permission_denied_response('No tienes permiso para reembolsar este pago')
            
            # Validar datos del reembolso
            serializer = PaymentRefundSerializer(data=request.data)
            if not serializer.is_valid():
                return validation_error_response(serializer.errors)
            
            # Procesar reembolso
            result = self.payment_service.refund_payment(
                payment,
                amount=serializer.validated_data.get('amount'),
                reason=serializer.validated_data['reason']
            )
            
            if result['success']:
                detail_serializer = PaymentDetailSerializer(result['payment'])
                return success_response(
                    data=detail_serializer.data,
                    message=result['message']
                )
            else:
                return error_response(result.get('error', 'Error al procesar el reembolso'))
        
        except ValueError as e:
            return error_response(str(e))
        except Exception as e:
            return error_response(
                f'Error al procesar el reembolso: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='my-earnings')
    def my_earnings(self, request):
        """
        Obtiene las ganancias del propietario.
        
        GET /api/payments/my-earnings/
        Query params opcionales: from_date, to_date
        """
        # Validar que el usuario sea propietario
        permission_error = check_user_type(
            request.user,
            'owner',
            'Solo los propietarios pueden ver ganancias'
        )
        if permission_error:
            return permission_error
        
        # Parsear filtros de fechas
        filters = {}
        
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
            earnings = self.payment_service.get_owner_earnings(
                str(request.user.id),
                filters
            )
            
            return success_response(data=earnings)
        except Exception as e:
            return error_response(
                f'Error al obtener ganancias: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """
        Obtiene estadísticas de pagos del usuario.
        
        GET /api/payments/statistics/
        Query params opcionales: from_date, to_date
        """
        # Parsear filtros de fechas
        filters = {}
        
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
            stats = self.payment_service.get_payment_statistics(
                request.user,
                filters
            )
            
            serializer = PaymentStatisticsSerializer(stats)
            return success_response(data=serializer.data)
        except Exception as e:
            return error_response(
                f'Error al obtener estadísticas: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
