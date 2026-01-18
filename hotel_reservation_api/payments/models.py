"""
Modelos de pagos y transacciones en PostgreSQL.
"""
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class Payment(models.Model):
    """
    Modelo principal para pagos de reservaciones.
    Almacena información del pago y su estado.
    """
    
    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pendiente"
        PROCESSING = "processing", "Procesando"
        COMPLETED = "completed", "Completado"
        FAILED = "failed", "Fallido"
        REFUNDED = "refunded", "Reembolsado"
        CANCELLED = "cancelled", "Cancelado"
    
    class PaymentMethod(models.TextChoices):
        CREDIT_CARD = "credit_card", "Tarjeta de Crédito"
        DEBIT_CARD = "debit_card", "Tarjeta de Débito"
        PAYPAL = "paypal", "PayPal"
        BANK_TRANSFER = "bank_transfer", "Transferencia Bancaria"
        OTHER = "other", "Otro"
    
    class PaymentGateway(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        PAYPAL = "paypal", "PayPal"
        MERCADOPAGO = "mercadopago", "MercadoPago"
        MANUAL = "manual", "Manual"
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID"
    )
    
    # Relaciones
    reservation_id = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="ID de Reservación",
        help_text="UUID de la reservación en MongoDB"
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name="Usuario"
    )
    
    # Información del pago
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Monto"
    )
    
    currency = models.CharField(
        max_length=3,
        default="USD",
        verbose_name="Moneda",
        help_text="Código ISO 4217 (USD, EUR, etc.)"
    )
    
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
        verbose_name="Estado"
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        verbose_name="Método de Pago"
    )
    
    payment_gateway = models.CharField(
        max_length=20,
        choices=PaymentGateway.choices,
        verbose_name="Pasarela de Pago"
    )
    
    # Información de la pasarela
    gateway_payment_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="ID de Pago en Pasarela",
        help_text="ID del pago en la pasarela (Stripe, PayPal, etc.)"
    )
    
    gateway_response = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Respuesta de Pasarela",
        help_text="Respuesta completa de la pasarela de pago"
    )
    
    # Detalles adicionales
    description = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )
    
    metadata = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Metadatos",
        help_text="Información adicional del pago"
    )
    
    # Campos de error
    error_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Código de Error"
    )
    
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name="Mensaje de Error"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de Actualización"
    )
    
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de Completado"
    )
    
    failed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de Fallo"
    )
    
    refunded_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Fecha de Reembolso"
    )
    
    class Meta:
        db_table = "payments"
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['reservation_id', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['gateway_payment_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.id} - {self.amount} {self.currency} - {self.status}"
    
    def is_completed(self):
        """Verifica si el pago está completado."""
        return self.status == self.PaymentStatus.COMPLETED
    
    def is_refundable(self):
        """Verifica si el pago puede ser reembolsado."""
        return self.status == self.PaymentStatus.COMPLETED
    
    def can_be_cancelled(self):
        """Verifica si el pago puede ser cancelado."""
        return self.status in [self.PaymentStatus.PENDING, self.PaymentStatus.PROCESSING]


class Transaction(models.Model):
    """
    Historial de transacciones y cambios de estado de pagos.
    Registra todas las interacciones con pasarelas de pago.
    """
    
    class TransactionType(models.TextChoices):
        CHARGE = "charge", "Cargo"
        REFUND = "refund", "Reembolso"
        VOID = "void", "Anulación"
        AUTHORIZATION = "authorization", "Autorización"
        CAPTURE = "capture", "Captura"
    
    class TransactionStatus(models.TextChoices):
        SUCCESS = "success", "Exitosa"
        FAILED = "failed", "Fallida"
        PENDING = "pending", "Pendiente"
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID"
    )
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="Pago"
    )
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        verbose_name="Tipo de Transacción"
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Monto"
    )
    
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING,
        verbose_name="Estado"
    )
    
    gateway_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="ID de Transacción en Pasarela"
    )
    
    error_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Código de Error"
    )
    
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name="Mensaje de Error"
    )
    
    response_data = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Datos de Respuesta",
        help_text="Respuesta completa de la pasarela"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="Notas",
        help_text="Notas adicionales sobre la transacción"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    
    class Meta:
        db_table = "transactions"
        verbose_name = "Transacción"
        verbose_name_plural = "Transacciones"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['payment', 'transaction_type']),
            models.Index(fields=['gateway_transaction_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Transaction {self.id} - {self.transaction_type} - {self.amount} - {self.status}"
    
    def is_successful(self):
        """Verifica si la transacción fue exitosa."""
        return self.status == self.TransactionStatus.SUCCESS


class PaymentMethod(models.Model):
    """
    Métodos de pago guardados del usuario (para futuro uso).
    Almacena tokens de pasarelas, no información sensible de tarjetas.
    """
    
    class PaymentType(models.TextChoices):
        CARD = "card", "Tarjeta"
        BANK_ACCOUNT = "bank_account", "Cuenta Bancaria"
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID"
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_methods',
        verbose_name="Usuario"
    )
    
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices,
        verbose_name="Tipo de Pago"
    )
    
    # Información de la tarjeta (solo últimos 4 dígitos)
    last_four = models.CharField(
        max_length=4,
        verbose_name="Últimos 4 Dígitos"
    )
    
    brand = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Marca",
        help_text="Visa, Mastercard, Amex, etc."
    )
    
    expiry_month = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Mes de Expiración"
    )
    
    expiry_year = models.IntegerField(
        blank=True,
        null=True,
        verbose_name="Año de Expiración"
    )
    
    # Token de la pasarela (NO almacenar información de tarjeta real)
    gateway_token = models.CharField(
        max_length=255,
        verbose_name="Token de Pasarela",
        help_text="Token proporcionado por la pasarela de pago"
    )
    
    gateway = models.CharField(
        max_length=20,
        verbose_name="Pasarela",
        help_text="Stripe, PayPal, etc."
    )
    
    is_default = models.BooleanField(
        default=False,
        verbose_name="Método Predeterminado"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de Actualización"
    )
    
    class Meta:
        db_table = "payment_methods"
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"
        ordering = ["-is_default", "-created_at"]
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['gateway_token']),
        ]
    
    def __str__(self):
        return f"{self.brand} •••• {self.last_four}"
    
    def save(self, *args, **kwargs):
        """Si se marca como predeterminado, desmarcar los demás."""
        if self.is_default:
            PaymentMethod.objects.filter(
                user=self.user,
                is_default=True
            ).update(is_default=False)
        super().save(*args, **kwargs)
