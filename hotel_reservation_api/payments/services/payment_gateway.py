"""
Clases abstractas y concretas para integración con pasarelas de pago.
Proporciona una interfaz uniforme para diferentes proveedores.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional
from decimal import Decimal


class PaymentGateway(ABC):
    """
    Clase abstracta para integración con pasarelas de pago.
    Define la interfaz que deben implementar todas las pasarelas.
    """
    
    @abstractmethod
    def charge(self, amount: Decimal, currency: str, payment_token: str, 
               metadata: Optional[Dict] = None) -> Dict:
        """
        Procesa un cargo en la pasarela de pago.
        
        Args:
            amount: Monto a cobrar
            currency: Código de moneda (USD, EUR, etc.)
            payment_token: Token de pago del cliente
            metadata: Información adicional
            
        Returns:
            Dict con resultado del cargo: {
                'success': bool,
                'transaction_id': str,
                'response': dict,
                'error': str (opcional)
            }
        """
        pass
    
    @abstractmethod
    def refund(self, transaction_id: str, amount: Optional[Decimal] = None, 
               reason: Optional[str] = None) -> Dict:
        """
        Procesa un reembolso.
        
        Args:
            transaction_id: ID de la transacción original
            amount: Monto a reembolsar (None para reembolso completo)
            reason: Razón del reembolso
            
        Returns:
            Dict con resultado del reembolso
        """
        pass
    
    @abstractmethod
    def verify(self, transaction_id: str) -> Dict:
        """
        Verifica el estado de una transacción.
        
        Args:
            transaction_id: ID de la transacción
            
        Returns:
            Dict con estado de la transacción
        """
        pass
    
    @abstractmethod
    def cancel(self, transaction_id: str) -> Dict:
        """
        Cancela una transacción pendiente.
        
        Args:
            transaction_id: ID de la transacción
            
        Returns:
            Dict con resultado de la cancelación
        """
        pass


class StripeGateway(PaymentGateway):
    """
    Implementación SIMULADA de la pasarela de Stripe.
    Para uso en desarrollo y pruebas sin necesidad de cuenta real de Stripe.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa el gateway simulado de Stripe.
        
        Args:
            api_key: No se usa en la simulación, solo por compatibilidad
        """
        import uuid
        import random
        self.uuid = uuid
        self.random = random
        # Simulador: almacenar transacciones en memoria
        self.transactions = {}
    
    def charge(self, amount: Decimal, currency: str, payment_token: str, 
               metadata: Optional[Dict] = None) -> Dict:
        """
        Simula un cargo con Stripe.
        
        Tokens especiales para pruebas:
        - 'tok_success' o cualquier otro: Pago exitoso
        - 'tok_fail': Pago fallido (tarjeta rechazada)
        - 'tok_insufficient': Fondos insuficientes
        - 'tok_expired': Tarjeta expirada
        """
        try:
            # Generar ID de transacción simulado
            transaction_id = f"ch_sim_{self.uuid.uuid4().hex[:24]}"
            
            # Simular diferentes escenarios basados en el token
            if payment_token == 'tok_fail':
                return {
                    'success': False,
                    'error': 'Su tarjeta fue rechazada',
                    'error_code': 'card_declined',
                    'response': {
                        'error': {
                            'type': 'card_error',
                            'code': 'card_declined',
                            'message': 'Su tarjeta fue rechazada'
                        }
                    }
                }
            elif payment_token == 'tok_insufficient':
                return {
                    'success': False,
                    'error': 'Fondos insuficientes',
                    'error_code': 'insufficient_funds',
                    'response': {
                        'error': {
                            'type': 'card_error',
                            'code': 'insufficient_funds',
                            'message': 'Su tarjeta tiene fondos insuficientes'
                        }
                    }
                }
            elif payment_token == 'tok_expired':
                return {
                    'success': False,
                    'error': 'Tarjeta expirada',
                    'error_code': 'expired_card',
                    'response': {
                        'error': {
                            'type': 'card_error',
                            'code': 'expired_card',
                            'message': 'Su tarjeta ha expirado'
                        }
                    }
                }
            
            # Pago exitoso (caso por defecto)
            # Guardar transacción en memoria
            transaction_data = {
                'id': transaction_id,
                'amount': int(amount * 100),  # Centavos
                'currency': currency.lower(),
                'status': 'succeeded',
                'metadata': metadata or {},
                'created': self._get_timestamp(),
                'refunded': False,
                'refund_amount': 0
            }
            self.transactions[transaction_id] = transaction_data
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'response': transaction_data,
                'status': 'succeeded'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error inesperado: {str(e)}",
                'response': {}
            }
    
    def refund(self, transaction_id: str, amount: Optional[Decimal] = None, 
               reason: Optional[str] = None) -> Dict:
        """Simula un reembolso con Stripe."""
        try:
            # Verificar que la transacción existe
            if transaction_id not in self.transactions:
                return {
                    'success': False,
                    'error': 'Transacción no encontrada',
                    'response': {}
                }
            
            original_transaction = self.transactions[transaction_id]
            
            # Verificar que no esté ya reembolsada
            if original_transaction['refunded']:
                return {
                    'success': False,
                    'error': 'Esta transacción ya fue reembolsada',
                    'response': {}
                }
            
            # Calcular monto del reembolso
            refund_amount_cents = int(amount * 100) if amount else original_transaction['amount']
            
            # Verificar que no exceda el monto original
            if refund_amount_cents > original_transaction['amount']:
                return {
                    'success': False,
                    'error': 'El monto del reembolso excede el cargo original',
                    'response': {}
                }
            
            # Generar ID de reembolso
            refund_id = f"re_sim_{self.uuid.uuid4().hex[:24]}"
            
            # Actualizar transacción original
            original_transaction['refunded'] = True
            original_transaction['refund_amount'] = refund_amount_cents
            
            # Crear datos del reembolso
            refund_data = {
                'id': refund_id,
                'amount': refund_amount_cents,
                'currency': original_transaction['currency'],
                'charge': transaction_id,
                'status': 'succeeded',
                'reason': reason or 'requested_by_customer',
                'created': self._get_timestamp()
            }
            
            return {
                'success': True,
                'transaction_id': refund_id,
                'response': refund_data,
                'status': 'succeeded'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error inesperado: {str(e)}",
                'response': {}
            }
    
    def verify(self, transaction_id: str) -> Dict:
        """Simula la verificación del estado de una transacción con Stripe."""
        try:
            # Verificar que la transacción existe
            if transaction_id not in self.transactions:
                return {
                    'success': False,
                    'error': 'Transacción no encontrada',
                    'response': {}
                }
            
            transaction = self.transactions[transaction_id]
            
            return {
                'success': True,
                'transaction_id': transaction['id'],
                'status': transaction['status'],
                'amount': Decimal(transaction['amount']) / 100,
                'currency': transaction['currency'].upper(),
                'response': transaction
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Error inesperado: {str(e)}",
                'response': {}
            }
    
    def cancel(self, transaction_id: str) -> Dict:
        """
        Simula la cancelación de un cargo.
        En la simulación, cancelar es equivalente a hacer un reembolso completo.
        """
        return self.refund(transaction_id)
    
    def _get_timestamp(self) -> int:
        """Genera un timestamp Unix simulado."""
        from datetime import datetime
        return int(datetime.now().timestamp())


class PayPalGateway(PaymentGateway):
    """
    Implementación de la pasarela de PayPal.
    Placeholder para futura implementación.
    """
    
    def __init__(self, client_id: Optional[str] = None, secret: Optional[str] = None):
        """Inicializa el gateway de PayPal."""
        self.client_id = client_id
        self.secret = secret
        # TODO: Implementar inicialización de PayPal SDK
    
    def charge(self, amount: Decimal, currency: str, payment_token: str, 
               metadata: Optional[Dict] = None) -> Dict:
        """Procesa un cargo con PayPal."""
        # TODO: Implementar integración con PayPal
        raise NotImplementedError("PayPal gateway no implementado aún")
    
    def refund(self, transaction_id: str, amount: Optional[Decimal] = None, 
               reason: Optional[str] = None) -> Dict:
        """Procesa un reembolso con PayPal."""
        # TODO: Implementar integración con PayPal
        raise NotImplementedError("PayPal gateway no implementado aún")
    
    def verify(self, transaction_id: str) -> Dict:
        """Verifica el estado de una transacción con PayPal."""
        # TODO: Implementar integración con PayPal
        raise NotImplementedError("PayPal gateway no implementado aún")
    
    def cancel(self, transaction_id: str) -> Dict:
        """Cancela una transacción con PayPal."""
        # TODO: Implementar integración con PayPal
        raise NotImplementedError("PayPal gateway no implementado aún")


class MercadoPagoGateway(PaymentGateway):
    """
    Implementación de la pasarela de MercadoPago.
    Placeholder para futura implementación.
    """
    
    def __init__(self, access_token: Optional[str] = None):
        """Inicializa el gateway de MercadoPago."""
        self.access_token = access_token
        # TODO: Implementar inicialización de MercadoPago SDK
    
    def charge(self, amount: Decimal, currency: str, payment_token: str, 
               metadata: Optional[Dict] = None) -> Dict:
        """Procesa un cargo con MercadoPago."""
        # TODO: Implementar integración con MercadoPago
        raise NotImplementedError("MercadoPago gateway no implementado aún")
    
    def refund(self, transaction_id: str, amount: Optional[Decimal] = None, 
               reason: Optional[str] = None) -> Dict:
        """Procesa un reembolso con MercadoPago."""
        # TODO: Implementar integración con MercadoPago
        raise NotImplementedError("MercadoPago gateway no implementado aún")
    
    def verify(self, transaction_id: str) -> Dict:
        """Verifica el estado de una transacción con MercadoPago."""
        # TODO: Implementar integración con MercadoPago
        raise NotImplementedError("MercadoPago gateway no implementado aún")
    
    def cancel(self, transaction_id: str) -> Dict:
        """Cancela una transacción con MercadoPago."""
        # TODO: Implementar integración con MercadoPago
        raise NotImplementedError("MercadoPago gateway no implementado aún")


def get_payment_gateway(gateway_name: str) -> PaymentGateway:
    """
    Factory function para obtener la instancia correcta de gateway.
    
    Args:
        gateway_name: Nombre del gateway (stripe, paypal, mercadopago)
        
    Returns:
        Instancia del gateway correspondiente
        
    Raises:
        ValueError: Si el gateway no está soportado
    """
    gateways = {
        'stripe': StripeGateway,
        'paypal': PayPalGateway,
        'mercadopago': MercadoPagoGateway,
    }
    
    gateway_class = gateways.get(gateway_name.lower())
    if not gateway_class:
        raise ValueError(f"Gateway '{gateway_name}' no soportado")
    
    return gateway_class()
