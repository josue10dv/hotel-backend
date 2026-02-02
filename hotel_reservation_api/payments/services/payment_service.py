"""
Servicio para la gestión de pagos en PostgreSQL.
Contiene toda la lógica de negocio y operaciones de base de datos.
"""
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal
from django.db import transaction as db_transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from payments.models import Payment, Transaction, PaymentMethod
from payments.services.payment_gateway import get_payment_gateway
from app.mongodb import mongo_db


class PaymentService:
    """
    Servicio para operaciones de pagos en PostgreSQL.
    Gestiona pagos, transacciones y sincronización con reservaciones.
    """
    
    def __init__(self):
        self.reservations_collection = mongo_db.db['reservations']
    
    def create_payment(self, payment_data: Dict, user) -> Payment:
        """
        Crea un nuevo registro de pago en PostgreSQL.
        
        Args:
            payment_data: Datos del pago
            user: Usuario que realiza el pago
            
        Returns:
            Instancia de Payment creada
            
        Raises:
            ValueError: Si hay errores de validación
        """
        # Obtener información de la reservación desde MongoDB
        reservation = self._get_reservation(payment_data['reservation_id'])
        if not reservation:
            raise ValueError("Reservación no encontrada")
        
        # Validar que el usuario sea el huésped de la reservación
        if str(reservation['guest_id']) != str(user.id):
            raise ValueError("No tienes permiso para pagar esta reservación")
        
        # Validar que la reservación esté en estado válido para pago
        if reservation['status'] not in ['pending', 'confirmed']:
            raise ValueError(
                f"No se puede pagar una reservación en estado '{reservation['status']}'"
            )
        
        # Validar que no exista un pago completado para esta reservación
        existing_payment = Payment.objects.filter(
            reservation_id=payment_data['reservation_id'],
            status=Payment.PaymentStatus.COMPLETED
        ).first()
        
        if existing_payment:
            raise ValueError("Ya existe un pago completado para esta reservación")
        
        # Crear el registro de pago
        payment = Payment.objects.create(
            reservation_id=payment_data['reservation_id'],
            user=user,
            amount=Decimal(str(reservation['total_price'])),
            currency=reservation.get('currency', 'USD'),
            status=Payment.PaymentStatus.PENDING,
            payment_method=payment_data['payment_method'],
            payment_gateway=payment_data['payment_gateway'],
            description=f"Pago por reservación {payment_data['reservation_id']}",
            metadata=payment_data.get('metadata', {})
        )
        
        return payment

    def create_payment_for_checkout(
        self,
        reservation_id: str,
        amount: Decimal,
        currency: str,
        user,
        payment_data: Dict,
    ) -> Payment:
        """
        Crea el registro de pago para checkout (reserva aún no existe en MongoDB).
        Solo se usa cuando el flujo es: cobrar primero, crear reserva solo si pago OK.
        """
        if amount <= 0:
            raise ValueError("El monto debe ser mayor a cero")
        existing = Payment.objects.filter(
            reservation_id=reservation_id,
            status=Payment.PaymentStatus.COMPLETED,
        ).first()
        if existing:
            raise ValueError("Ya existe un pago completado para esta reservación")
        return Payment.objects.create(
            reservation_id=reservation_id,
            user=user,
            amount=amount,
            currency=currency or "USD",
            status=Payment.PaymentStatus.PENDING,
            payment_method=payment_data['payment_method'],
            payment_gateway=payment_data['payment_gateway'],
            description=f"Pago por reservación {reservation_id}",
            metadata=payment_data.get('metadata') or {},
        )

    def process_payment(self, payment: Payment, payment_token: str) -> Dict:
        """
        Procesa un pago con la pasarela correspondiente.
        
        Args:
            payment: Instancia de Payment
            payment_token: Token de pago del cliente
            
        Returns:
            Dict con resultado del procesamiento
        """
        try:
            # Actualizar estado a procesando
            payment.status = Payment.PaymentStatus.PROCESSING
            payment.save()
            
            # Obtener gateway y procesar pago
            gateway = get_payment_gateway(payment.payment_gateway)
            
            result = gateway.charge(
                amount=payment.amount,
                currency=payment.currency,
                payment_token=payment_token,
                metadata={
                    'payment_id': str(payment.id),
                    'reservation_id': payment.reservation_id,
                    'user_id': str(payment.user.id)
                }
            )
            
            # Crear transacción
            transaction_data = {
                'payment': payment,
                'transaction_type': Transaction.TransactionType.CHARGE,
                'amount': payment.amount,
                'response_data': result.get('response', {})
            }
            
            if result['success']:
                # Pago exitoso
                with db_transaction.atomic():
                    payment.status = Payment.PaymentStatus.COMPLETED
                    payment.gateway_payment_id = result['transaction_id']
                    payment.gateway_response = result.get('response', {})
                    payment.completed_at = timezone.now()
                    payment.save()
                    
                    # Crear transacción exitosa
                    transaction_data.update({
                        'status': Transaction.TransactionStatus.SUCCESS,
                        'gateway_transaction_id': result['transaction_id']
                    })
                    Transaction.objects.create(**transaction_data)
                    
                    # Actualizar estado de pago en la reservación
                    self._update_reservation_payment_status(
                        payment.reservation_id,
                        'paid'
                    )
                
                return {
                    'success': True,
                    'payment': payment,
                    'transaction_id': result['transaction_id'],
                    'message': 'Pago procesado exitosamente'
                }
            else:
                # Pago fallido
                with db_transaction.atomic():
                    payment.status = Payment.PaymentStatus.FAILED
                    payment.error_code = result.get('error_code', 'UNKNOWN')
                    payment.error_message = result.get('error', 'Error desconocido')
                    payment.failed_at = timezone.now()
                    payment.save()
                    
                    # Crear transacción fallida
                    transaction_data.update({
                        'status': Transaction.TransactionStatus.FAILED,
                        'error_code': result.get('error_code'),
                        'error_message': result.get('error')
                    })
                    Transaction.objects.create(**transaction_data)
                
                return {
                    'success': False,
                    'payment': payment,
                    'error': result.get('error', 'Error al procesar el pago'),
                    'error_code': result.get('error_code')
                }
        
        except Exception as e:
            # Error inesperado
            with db_transaction.atomic():
                payment.status = Payment.PaymentStatus.FAILED
                payment.error_message = str(e)
                payment.failed_at = timezone.now()
                payment.save()
                
                Transaction.objects.create(
                    payment=payment,
                    transaction_type=Transaction.TransactionType.CHARGE,
                    amount=payment.amount,
                    status=Transaction.TransactionStatus.FAILED,
                    error_message=str(e)
                )
            
            return {
                'success': False,
                'payment': payment,
                'error': f'Error inesperado: {str(e)}'
            }
    
    def refund_payment(self, payment: Payment, amount: Optional[Decimal] = None,
                      reason: str = '') -> Dict:
        """
        Procesa un reembolso de pago.
        
        Args:
            payment: Instancia de Payment
            amount: Monto a reembolsar (None para reembolso completo)
            reason: Razón del reembolso
            
        Returns:
            Dict con resultado del reembolso
        """
        # Validar que el pago pueda ser reembolsado
        if not payment.is_refundable():
            raise ValueError(
                f"El pago en estado '{payment.status}' no puede ser reembolsado"
            )
        
        # Si no se especifica monto, reembolsar todo
        refund_amount = amount or payment.amount
        
        # Validar que el monto no exceda el pago original
        if refund_amount > payment.amount:
            raise ValueError(
                "El monto del reembolso no puede exceder el monto del pago original"
            )
        
        try:
            # Procesar reembolso con la pasarela
            gateway = get_payment_gateway(payment.payment_gateway)
            
            result = gateway.refund(
                transaction_id=payment.gateway_payment_id,
                amount=refund_amount,
                reason=reason
            )
            
            # Crear transacción de reembolso
            transaction_data = {
                'payment': payment,
                'transaction_type': Transaction.TransactionType.REFUND,
                'amount': refund_amount,
                'notes': reason,
                'response_data': result.get('response', {})
            }
            
            if result['success']:
                # Reembolso exitoso
                with db_transaction.atomic():
                    payment.status = Payment.PaymentStatus.REFUNDED
                    payment.refunded_at = timezone.now()
                    payment.save()
                    
                    # Crear transacción exitosa
                    transaction_data.update({
                        'status': Transaction.TransactionStatus.SUCCESS,
                        'gateway_transaction_id': result['transaction_id']
                    })
                    Transaction.objects.create(**transaction_data)
                    
                    # Actualizar estado de pago en la reservación
                    self._update_reservation_payment_status(
                        payment.reservation_id,
                        'refunded'
                    )
                
                return {
                    'success': True,
                    'payment': payment,
                    'transaction_id': result['transaction_id'],
                    'message': 'Reembolso procesado exitosamente'
                }
            else:
                # Reembolso fallido
                transaction_data.update({
                    'status': Transaction.TransactionStatus.FAILED,
                    'error_code': result.get('error_code'),
                    'error_message': result.get('error')
                })
                Transaction.objects.create(**transaction_data)
                
                return {
                    'success': False,
                    'error': result.get('error', 'Error al procesar el reembolso')
                }
        
        except Exception as e:
            # Error inesperado
            Transaction.objects.create(
                payment=payment,
                transaction_type=Transaction.TransactionType.REFUND,
                amount=refund_amount,
                status=Transaction.TransactionStatus.FAILED,
                error_message=str(e),
                notes=reason
            )
            
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }
    
    def verify_payment(self, payment: Payment) -> Dict:
        """
        Verifica el estado de un pago con la pasarela.
        
        Args:
            payment: Instancia de Payment
            
        Returns:
            Dict con estado actualizado del pago
        """
        if not payment.gateway_payment_id:
            raise ValueError("El pago no tiene un ID de transacción en la pasarela")
        
        try:
            gateway = get_payment_gateway(payment.payment_gateway)
            result = gateway.verify(payment.gateway_payment_id)
            
            if result['success']:
                # Actualizar información del pago si es necesario
                gateway_status = result.get('status', '')
                
                # Mapear estados de la pasarela a nuestros estados
                if gateway_status in ['succeeded', 'paid']:
                    if payment.status != Payment.PaymentStatus.COMPLETED:
                        payment.status = Payment.PaymentStatus.COMPLETED
                        payment.completed_at = timezone.now()
                        payment.save()
                        
                        self._update_reservation_payment_status(
                            payment.reservation_id,
                            'paid'
                        )
                
                return {
                    'success': True,
                    'status': result.get('status'),
                    'amount': result.get('amount'),
                    'currency': result.get('currency'),
                    'payment': payment
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Error al verificar el pago')
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': f'Error inesperado: {str(e)}'
            }
    
    def get_user_payments(self, user, filters: Optional[Dict] = None) -> List[Payment]:
        """
        Obtiene todos los pagos de un usuario.
        
        Args:
            user: Usuario
            filters: Filtros adicionales (status, from_date, to_date)
            
        Returns:
            QuerySet de Payment
        """
        query = Payment.objects.filter(user=user)
        
        if filters:
            if 'status' in filters:
                query = query.filter(status=filters['status'])
            if 'from_date' in filters:
                query = query.filter(created_at__gte=filters['from_date'])
            if 'to_date' in filters:
                query = query.filter(created_at__lte=filters['to_date'])
        
        return query.select_related('user').order_by('-created_at')
    
    def get_owner_earnings(self, owner_id: str, filters: Optional[Dict] = None) -> Dict:
        """
        Obtiene las ganancias de un propietario.
        
        Args:
            owner_id: UUID del propietario
            filters: Filtros adicionales
            
        Returns:
            Dict con estadísticas de ganancias
        """
        # Obtener reservaciones del propietario desde MongoDB
        query = {'owner_id': str(owner_id)}
        
        if filters:
            if 'from_date' in filters:
                query['created_at'] = {'$gte': filters['from_date']}
            if 'to_date' in filters:
                if 'created_at' in query:
                    query['created_at']['$lte'] = filters['to_date']
                else:
                    query['created_at'] = {'$lte': filters['to_date']}
        
        reservations = self.reservations_collection.find(query)
        reservation_ids = [r['reservation_id'] for r in reservations]
        
        # Obtener pagos de esas reservaciones
        payments = Payment.objects.filter(
            reservation_id__in=reservation_ids,
            status=Payment.PaymentStatus.COMPLETED
        )
        
        # Calcular estadísticas
        stats = payments.aggregate(
            total_earnings=Sum('amount'),
            total_payments=Count('id')
        )
        
        return {
            'total_earnings': stats['total_earnings'] or Decimal('0.00'),
            'total_payments': stats['total_payments'] or 0,
            'currency': 'USD'  # Por defecto
        }
    
    def get_payment_statistics(self, user=None, filters: Optional[Dict] = None) -> Dict:
        """
        Obtiene estadísticas de pagos.
        
        Args:
            user: Usuario (opcional, para filtrar por usuario)
            filters: Filtros adicionales
            
        Returns:
            Dict con estadísticas
        """
        query = Payment.objects.all()
        
        if user:
            query = query.filter(user=user)
        
        if filters:
            if 'from_date' in filters:
                query = query.filter(created_at__gte=filters['from_date'])
            if 'to_date' in filters:
                query = query.filter(created_at__lte=filters['to_date'])
        
        # Calcular estadísticas por estado
        completed = query.filter(status=Payment.PaymentStatus.COMPLETED).aggregate(
            count=Count('id'),
            total=Sum('amount')
        )
        
        pending = query.filter(status=Payment.PaymentStatus.PENDING).aggregate(
            count=Count('id'),
            total=Sum('amount')
        )
        
        failed = query.filter(status=Payment.PaymentStatus.FAILED).aggregate(
            count=Count('id')
        )
        
        refunded = query.filter(status=Payment.PaymentStatus.REFUNDED).aggregate(
            count=Count('id'),
            total=Sum('amount')
        )
        
        total = query.aggregate(
            count=Count('id'),
            total=Sum('amount')
        )
        
        return {
            'total_payments': total['count'] or 0,
            'total_amount': total['total'] or Decimal('0.00'),
            'completed_payments': completed['count'] or 0,
            'completed_amount': completed['total'] or Decimal('0.00'),
            'pending_payments': pending['count'] or 0,
            'pending_amount': pending['total'] or Decimal('0.00'),
            'failed_payments': failed['count'] or 0,
            'refunded_payments': refunded['count'] or 0,
            'refunded_amount': refunded['total'] or Decimal('0.00'),
            'currency': 'USD'
        }
    
    def _get_reservation(self, reservation_id: str) -> Optional[Dict]:
        """Obtiene una reservación desde MongoDB."""
        return self.reservations_collection.find_one({'reservation_id': reservation_id})
    
    def _update_reservation_payment_status(self, reservation_id: str, 
                                          payment_status: str):
        """Actualiza el estado de pago de una reservación en MongoDB."""
        self.reservations_collection.update_one(
            {'reservation_id': reservation_id},
            {'$set': {
                'payment_status': payment_status,
                'updated_at': datetime.utcnow()
            }}
        )
