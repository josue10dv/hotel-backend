"""
Serializers para pagos y transacciones.
Validan y transforman datos de entrada/salida para la API.
"""
from rest_framework import serializers
from payments.models import Payment, Transaction, PaymentMethod


class PaymentCreateSerializer(serializers.Serializer):
    """Serializer para crear un nuevo pago."""
    
    reservation_id = serializers.CharField(
        required=True,
        help_text="UUID de la reservación"
    )
    
    payment_method = serializers.ChoiceField(
        choices=Payment.PaymentMethod.choices,
        required=True,
        help_text="Método de pago"
    )
    
    payment_gateway = serializers.ChoiceField(
        choices=Payment.PaymentGateway.choices,
        default=Payment.PaymentGateway.STRIPE,
        help_text="Pasarela de pago a utilizar"
    )
    
    # Token de pago de la pasarela (generado en el frontend)
    payment_token = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Token de pago proporcionado por la pasarela (Stripe, PayPal, etc.)"
    )
    
    # Campos opcionales
    save_payment_method = serializers.BooleanField(
        default=False,
        help_text="Guardar método de pago para uso futuro"
    )
    
    metadata = serializers.JSONField(
        required=False,
        help_text="Metadatos adicionales"
    )
    
    def validate_reservation_id(self, value):
        """Valida que el reservation_id no esté vacío."""
        if not value or not value.strip():
            raise serializers.ValidationError("El ID de reservación es requerido")
        return value.strip()


class PaymentListSerializer(serializers.ModelSerializer):
    """Serializer para listar pagos (vista simplificada)."""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'reservation_id',
            'user_email',
            'amount',
            'currency',
            'status',
            'status_display',
            'payment_method',
            'payment_method_display',
            'payment_gateway',
            'created_at',
            'completed_at'
        ]
        read_only_fields = fields


class PaymentDetailSerializer(serializers.ModelSerializer):
    """Serializer para detalle completo de un pago."""
    
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    payment_gateway_display = serializers.CharField(source='get_payment_gateway_display', read_only=True)
    is_completed = serializers.BooleanField(read_only=True)
    is_refundable = serializers.BooleanField(read_only=True)
    can_be_cancelled = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'reservation_id',
            'user_email',
            'user_name',
            'amount',
            'currency',
            'status',
            'status_display',
            'payment_method',
            'payment_method_display',
            'payment_gateway',
            'payment_gateway_display',
            'gateway_payment_id',
            'description',
            'metadata',
            'error_code',
            'error_message',
            'is_completed',
            'is_refundable',
            'can_be_cancelled',
            'created_at',
            'updated_at',
            'completed_at',
            'failed_at',
            'refunded_at'
        ]
        read_only_fields = fields
    
    def get_user_name(self, obj):
        """Obtiene el nombre completo del usuario."""
        if obj.user.first_name or obj.user.last_name:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return obj.user.username


class PaymentRefundSerializer(serializers.Serializer):
    """Serializer para procesar un reembolso."""
    
    amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        help_text="Monto a reembolsar (si no se especifica, se reembolsa el monto completo)"
    )
    
    reason = serializers.CharField(
        required=True,
        help_text="Razón del reembolso"
    )
    
    def validate_amount(self, value):
        """Valida que el monto sea positivo."""
        if value is not None and value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a cero")
        return value
    
    def validate(self, data):
        """Validaciones adicionales."""
        # Validar que la razón no esté vacía
        if not data.get('reason', '').strip():
            raise serializers.ValidationError({
                'reason': 'Debe proporcionar una razón para el reembolso'
            })
        return data


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer para transacciones."""
    
    payment_id = serializers.UUIDField(source='payment.id', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_successful = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id',
            'payment_id',
            'transaction_type',
            'transaction_type_display',
            'amount',
            'status',
            'status_display',
            'gateway_transaction_id',
            'error_code',
            'error_message',
            'response_data',
            'notes',
            'is_successful',
            'created_at'
        ]
        read_only_fields = fields


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer para métodos de pago guardados."""
    
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id',
            'payment_type',
            'payment_type_display',
            'last_four',
            'brand',
            'expiry_month',
            'expiry_year',
            'is_expired',
            'gateway',
            'is_default',
            'is_active',
            'created_at'
        ]
        read_only_fields = [
            'id',
            'payment_type',
            'last_four',
            'brand',
            'expiry_month',
            'expiry_year',
            'gateway',
            'created_at'
        ]
    
    def get_is_expired(self, obj):
        """Verifica si la tarjeta está vencida."""
        if obj.expiry_month and obj.expiry_year:
            from datetime import datetime
            now = datetime.now()
            if obj.expiry_year < now.year:
                return True
            if obj.expiry_year == now.year and obj.expiry_month < now.month:
                return True
        return False


class PaymentStatisticsSerializer(serializers.Serializer):
    """Serializer para estadísticas de pagos."""
    
    total_payments = serializers.IntegerField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    completed_payments = serializers.IntegerField(read_only=True)
    completed_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    pending_payments = serializers.IntegerField(read_only=True)
    pending_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    failed_payments = serializers.IntegerField(read_only=True)
    refunded_payments = serializers.IntegerField(read_only=True)
    refunded_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    currency = serializers.CharField(read_only=True)
