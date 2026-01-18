"""
Configuración del panel de administración de Django para pagos.
"""
from django.contrib import admin
from .models import Payment, Transaction, PaymentMethod


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Administración de pagos."""
    
    list_display = [
        'id', 'user', 'reservation_id', 'amount', 'currency',
        'status', 'payment_method', 'payment_gateway', 'created_at'
    ]
    list_filter = ['status', 'payment_method', 'payment_gateway', 'created_at']
    search_fields = ['id', 'reservation_id', 'user__email', 'gateway_payment_id']
    readonly_fields = ['id', 'created_at', 'updated_at', 'completed_at', 'failed_at', 'refunded_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('id', 'reservation_id', 'user', 'description')
        }),
        ('Detalles del Pago', {
            'fields': ('amount', 'currency', 'status', 'payment_method', 'payment_gateway')
        }),
        ('Información de Pasarela', {
            'fields': ('gateway_payment_id', 'gateway_response')
        }),
        ('Errores', {
            'fields': ('error_code', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at', 'completed_at', 'failed_at', 'refunded_at')
        }),
    )


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Administración de transacciones."""
    
    list_display = [
        'id', 'payment', 'transaction_type', 'amount',
        'status', 'gateway_transaction_id', 'created_at'
    ]
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['id', 'payment__id', 'gateway_transaction_id']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('id', 'payment', 'transaction_type', 'amount', 'status')
        }),
        ('Información de Pasarela', {
            'fields': ('gateway_transaction_id', 'response_data')
        }),
        ('Errores', {
            'fields': ('error_code', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('Fechas', {
            'fields': ('created_at',)
        }),
    )


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Administración de métodos de pago guardados."""
    
    list_display = [
        'id', 'user', 'payment_type', 'brand', 'last_four',
        'is_default', 'is_active', 'gateway', 'created_at'
    ]
    list_filter = ['payment_type', 'is_default', 'is_active', 'gateway', 'created_at']
    search_fields = ['id', 'user__email', 'last_four', 'gateway_token']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('id', 'user', 'payment_type', 'gateway')
        }),
        ('Detalles de Tarjeta', {
            'fields': ('brand', 'last_four', 'expiry_month', 'expiry_year')
        }),
        ('Token', {
            'fields': ('gateway_token',)
        }),
        ('Estado', {
            'fields': ('is_default', 'is_active')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at')
        }),
    )
