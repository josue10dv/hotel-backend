"""
Serializers para reservaciones.
Validan y transforman datos de entrada/salida para la API.
"""
from rest_framework import serializers
from datetime import datetime, timedelta
from django.utils import timezone


class GuestDetailsSerializer(serializers.Serializer):
    """Serializer para detalles del huésped."""
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    special_requests = serializers.CharField(required=False, allow_blank=True)


class ReservationCreateSerializer(serializers.Serializer):
    """Serializer para crear una nueva reservación."""
    hotel_id = serializers.CharField(required=True)
    room_id = serializers.CharField(required=False, allow_blank=True, help_text="Opcional: ID de habitación específica. Si no se proporciona, se asignará la primera disponible.")
    check_in = serializers.DateTimeField(required=True)
    check_out = serializers.DateTimeField(required=True)
    number_of_guests = serializers.IntegerField(required=True, min_value=1)
    guest_details = GuestDetailsSerializer(required=True)
    special_requests = serializers.CharField(required=False, allow_blank=True)
    
    def validate_check_in(self, value):
        """Valida que la fecha de entrada no sea en el pasado."""
        # Usar timezone.now() para obtener datetime aware compatible con value
        now = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # Asegurar que value también sea aware para la comparación
        value_date = value.replace(hour=0, minute=0, second=0, microsecond=0)
        if value_date < now:
            raise serializers.ValidationError(
                "La fecha de entrada no puede ser en el pasado"
            )
        return value
    
    def validate(self, data):
        """Valida que las fechas sean consistentes."""
        check_in = data.get('check_in')
        check_out = data.get('check_out')
        
        if check_out <= check_in:
            raise serializers.ValidationError({
                'check_out': 'La fecha de salida debe ser posterior a la fecha de entrada'
            })
        
        # Validar que no sea más de 1 año en el futuro
        # Usar timezone.now() para datetime aware
        max_date = timezone.now() + timedelta(days=365)
        if check_in > max_date:
            raise serializers.ValidationError({
                'check_in': 'No se pueden hacer reservaciones con más de un año de anticipación'
            })
        
        return data


class CheckoutSerializer(serializers.Serializer):
    """
    Serializer para checkout: reservación + pago en un solo paso.
    La reserva solo se guarda en backend cuando el pago es exitoso (paid).
    """
    # Campos de reservación (mismos que ReservationCreateSerializer)
    hotel_id = serializers.CharField(required=True)
    room_id = serializers.CharField(required=True)
    check_in = serializers.DateTimeField(required=True)
    check_out = serializers.DateTimeField(required=True)
    number_of_guests = serializers.IntegerField(required=True, min_value=1)
    guest_details = GuestDetailsSerializer(required=True)
    special_requests = serializers.CharField(required=False, allow_blank=True)
    # Campos de pago
    payment_method = serializers.ChoiceField(
        choices=[
            ('credit_card', 'Tarjeta de Crédito'),
            ('debit_card', 'Tarjeta de Débito'),
            ('paypal', 'PayPal'),
            ('bank_transfer', 'Transferencia Bancaria'),
            ('other', 'Otro'),
        ],
        required=True,
    )
    payment_gateway = serializers.ChoiceField(
        choices=[
            ('stripe', 'Stripe'),
            ('paypal', 'PayPal'),
            ('mercadopago', 'MercadoPago'),
            ('manual', 'Manual'),
        ],
        default='stripe',
    )
    payment_token = serializers.CharField(required=True, allow_blank=False)
    save_payment_method = serializers.BooleanField(default=False, required=False)
    metadata = serializers.JSONField(required=False)

    def validate_check_in(self, value):
        now = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        value_date = value.replace(hour=0, minute=0, second=0, microsecond=0)
        if value_date < now:
            raise serializers.ValidationError(
                "La fecha de entrada no puede ser en el pasado"
            )
        return value

    def validate(self, data):
        check_in = data.get('check_in')
        check_out = data.get('check_out')
        if check_out <= check_in:
            raise serializers.ValidationError({
                'check_out': 'La fecha de salida debe ser posterior a la fecha de entrada'
            })
        max_date = timezone.now() + timedelta(days=365)
        if check_in > max_date:
            raise serializers.ValidationError({
                'check_in': 'No se pueden hacer reservaciones con más de un año de anticipación'
            })
        return data


class ReservationListSerializer(serializers.Serializer):
    """Serializer para listar reservaciones (vista simplificada)."""
    id = serializers.CharField(read_only=True)
    reservation_id = serializers.CharField(read_only=True)
    hotel_id = serializers.CharField(read_only=True)
    room_id = serializers.CharField(read_only=True)
    check_in = serializers.DateTimeField(read_only=True)
    check_out = serializers.DateTimeField(read_only=True)
    nights = serializers.IntegerField(read_only=True)
    number_of_guests = serializers.IntegerField(read_only=True)
    total_price = serializers.FloatField(read_only=True)
    currency = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    payment_status = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class ReservationDetailSerializer(serializers.Serializer):
    """Serializer para detalle completo de una reservación."""
    id = serializers.CharField(read_only=True)
    reservation_id = serializers.CharField(read_only=True)
    hotel_id = serializers.CharField(read_only=True)
    room_id = serializers.CharField(read_only=True)
    guest_id = serializers.CharField(read_only=True)
    owner_id = serializers.CharField(read_only=True)
    check_in = serializers.DateTimeField(read_only=True)
    check_out = serializers.DateTimeField(read_only=True)
    nights = serializers.IntegerField(read_only=True)
    number_of_guests = serializers.IntegerField(read_only=True)
    guest_details = GuestDetailsSerializer(read_only=True)
    price_per_night = serializers.FloatField(read_only=True)
    total_price = serializers.FloatField(read_only=True)
    currency = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    payment_status = serializers.CharField(read_only=True)
    special_requests = serializers.CharField(read_only=True)
    cancellation_reason = serializers.CharField(read_only=True, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    cancelled_at = serializers.DateTimeField(read_only=True, allow_null=True)
    confirmed_at = serializers.DateTimeField(read_only=True, allow_null=True)


class ReservationUpdateSerializer(serializers.Serializer):
    """Serializer para actualizar el estado de una reservación."""
    status = serializers.ChoiceField(
        choices=['confirmed', 'cancelled', 'completed', 'rejected'],
        required=True
    )
    cancellation_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Razón de cancelación (requerido si status es 'cancelled')"
    )
    
    def validate(self, data):
        """Valida que se incluya razón si se cancela."""
        if data.get('status') == 'cancelled' and not data.get('cancellation_reason'):
            raise serializers.ValidationError({
                'cancellation_reason': 'Debe proporcionar una razón para cancelar'
            })
        return data


class CheckAvailabilitySerializer(serializers.Serializer):
    """Serializer para verificar disponibilidad de una habitación."""
    hotel_id = serializers.CharField(required=True)
    room_id = serializers.CharField(required=True)
    check_in = serializers.DateTimeField(required=True)
    check_out = serializers.DateTimeField(required=True)
    
    def validate_check_in(self, value):
        """Valida que la fecha de entrada no sea en el pasado."""
        # Usar timezone.now() para obtener datetime aware compatible con value
        now = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        # Asegurar que value también sea aware para la comparación
        value_date = value.replace(hour=0, minute=0, second=0, microsecond=0)
        if value_date < now:
            raise serializers.ValidationError(
                "La fecha de entrada no puede ser en el pasado"
            )
        return value
    
    def validate(self, data):
        """Valida que las fechas sean consistentes."""
        check_in = data.get('check_in')
        check_out = data.get('check_out')
        
        if check_out <= check_in:
            raise serializers.ValidationError({
                'check_out': 'La fecha de salida debe ser posterior a la fecha de entrada'
            })
        
        return data
