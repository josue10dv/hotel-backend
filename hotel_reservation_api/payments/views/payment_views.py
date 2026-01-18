"""
Views para la gestión de pagos.
Implementa endpoints REST usando ViewSets de Django REST Framework.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
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
from datetime import datetime


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
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
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
                return Response(
                    {
                        'message': 'Pago creado en estado pendiente',
                        'data': detail_serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )
            
            # Procesar el pago con la pasarela
            result = self.payment_service.process_payment(payment, payment_token)
            
            if result['success']:
                detail_serializer = PaymentDetailSerializer(result['payment'])
                return Response(
                    {
                        'message': result['message'],
                        'data': detail_serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                detail_serializer = PaymentDetailSerializer(result['payment'])
                return Response(
                    {
                        'error': result['error'],
                        'error_code': result.get('error_code'),
                        'data': detail_serializer.data
                    },
                    status=status.HTTP_402_PAYMENT_REQUIRED
                )
        
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error al procesar el pago: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def list(self, request):
        """
        Lista todos los pagos del usuario autenticado.
        
        GET /api/payments/
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
            payments = self.payment_service.get_user_payments(
                request.user,
                filters
            )
            serializer = PaymentListSerializer(payments, many=True)
            return Response(
                {
                    'count': payments.count(),
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Error al obtener pagos: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
                    return Response(
                        {'error': 'No tienes permiso para ver este pago'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            serializer = PaymentDetailSerializer(payment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'Error al obtener el pago: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
                return Response(
                    {'error': 'No tienes permiso para verificar este pago'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            result = self.payment_service.verify_payment(payment)
            
            if result['success']:
                serializer = PaymentDetailSerializer(result['payment'])
                return Response(
                    {
                        'message': 'Estado del pago verificado',
                        'gateway_status': result.get('status'),
                        'data': serializer.data
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': result.get('error', 'Error al verificar el pago')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error al verificar el pago: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
                    return Response(
                        {'error': 'No tienes permiso para ver las transacciones'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            transactions = payment.transactions.all().order_by('-created_at')
            serializer = TransactionSerializer(transactions, many=True)
            
            return Response(
                {
                    'count': transactions.count(),
                    'data': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Error al obtener transacciones: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
        if not hasattr(request.user, 'user_type') or request.user.user_type != 'owner':
            return Response(
                {'error': 'Solo los propietarios pueden procesar reembolsos'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            payment = get_object_or_404(Payment, pk=pk)
            
            # Verificar que el propietario sea dueño de la reservación
            reservation = self.payment_service._get_reservation(payment.reservation_id)
            if not reservation or str(reservation['owner_id']) != str(request.user.id):
                return Response(
                    {'error': 'No tienes permiso para reembolsar este pago'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Validar datos del reembolso
            serializer = PaymentRefundSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Procesar reembolso
            result = self.payment_service.refund_payment(
                payment,
                amount=serializer.validated_data.get('amount'),
                reason=serializer.validated_data['reason']
            )
            
            if result['success']:
                detail_serializer = PaymentDetailSerializer(result['payment'])
                return Response(
                    {
                        'message': result['message'],
                        'data': detail_serializer.data
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': result.get('error', 'Error al procesar el reembolso')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Error al procesar el reembolso: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='my-earnings')
    def my_earnings(self, request):
        """
        Obtiene las ganancias del propietario.
        
        GET /api/payments/my-earnings/
        Query params opcionales: from_date, to_date
        """
        # Validar que el usuario sea propietario
        if not hasattr(request.user, 'user_type') or request.user.user_type != 'owner':
            return Response(
                {'error': 'Solo los propietarios pueden ver ganancias'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Obtener filtros de query params
        filters = {}
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
            earnings = self.payment_service.get_owner_earnings(
                str(request.user.id),
                filters
            )
            
            return Response(earnings, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'Error al obtener ganancias: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """
        Obtiene estadísticas de pagos del usuario.
        
        GET /api/payments/statistics/
        Query params opcionales: from_date, to_date
        """
        # Obtener filtros de query params
        filters = {}
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
            stats = self.payment_service.get_payment_statistics(
                request.user,
                filters
            )
            
            serializer = PaymentStatisticsSerializer(stats)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'Error al obtener estadísticas: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
