"""
Serializers para la gestión de reseñas.
Valida y serializa datos entre la API REST y MongoDB.
"""
from rest_framework import serializers
from reviews.schemas.review_schema import ReviewSchema


class RatingBreakdownSerializer(serializers.Serializer):
    """
    Serializer para el desglose de calificaciones por categoría.
    
    Aplicando DRY, centraliza la validación de ratings en todas las categorías.
    """
    cleanliness = serializers.FloatField(
        min_value=ReviewSchema.MIN_RATING,
        max_value=ReviewSchema.MAX_RATING,
        required=False,
        help_text="Calificación de limpieza (1-5)"
    )
    communication = serializers.FloatField(
        min_value=ReviewSchema.MIN_RATING,
        max_value=ReviewSchema.MAX_RATING,
        required=False,
        help_text="Calificación de comunicación (1-5)"
    )
    check_in = serializers.FloatField(
        min_value=ReviewSchema.MIN_RATING,
        max_value=ReviewSchema.MAX_RATING,
        required=False,
        help_text="Calificación de proceso de check-in (1-5)"
    )
    accuracy = serializers.FloatField(
        min_value=ReviewSchema.MIN_RATING,
        max_value=ReviewSchema.MAX_RATING,
        required=False,
        help_text="Calificación de precisión de la descripción (1-5)"
    )
    location = serializers.FloatField(
        min_value=ReviewSchema.MIN_RATING,
        max_value=ReviewSchema.MAX_RATING,
        required=False,
        help_text="Calificación de ubicación (1-5)"
    )
    value = serializers.FloatField(
        min_value=ReviewSchema.MIN_RATING,
        max_value=ReviewSchema.MAX_RATING,
        required=False,
        help_text="Calificación de relación calidad-precio (1-5)"
    )


class ReviewResponseSerializer(serializers.Serializer):
    """Serializer para la respuesta del propietario."""
    owner_id = serializers.CharField(read_only=True)
    comment = serializers.CharField(
        max_length=1000,
        help_text="Respuesta del propietario"
    )
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class ReviewSerializer(serializers.Serializer):
    """
    Serializer completo para reseñas con todos los campos.
    Se usa para lectura de datos.
    """
    id = serializers.CharField(read_only=True, source='_id')
    hotel_id = serializers.CharField(read_only=True)
    user_id = serializers.CharField(read_only=True)
    reservation_id = serializers.CharField(read_only=True, allow_null=True)
    rating = serializers.FloatField(
        min_value=ReviewSchema.MIN_RATING,
        max_value=ReviewSchema.MAX_RATING
    )
    rating_breakdown = RatingBreakdownSerializer()
    title = serializers.CharField(max_length=200, allow_blank=True)
    comment = serializers.CharField(max_length=2000, allow_blank=True)
    pros = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        allow_empty=True,
        help_text="Lista de aspectos positivos"
    )
    cons = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        allow_empty=True,
        help_text="Lista de aspectos negativos"
    )
    images = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=True,
        help_text="URLs de imágenes"
    )
    response = ReviewResponseSerializer(read_only=True, allow_null=True)
    status = serializers.ChoiceField(
        choices=ReviewSchema.STATUSES,
        read_only=True
    )
    helpful_count = serializers.IntegerField(read_only=True, default=0)
    unhelpful_count = serializers.IntegerField(read_only=True, default=0)
    verified_stay = serializers.BooleanField(read_only=True, default=False)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    
    # Campos adicionales calculados
    user_found_helpful = serializers.BooleanField(read_only=True, required=False)


class ReviewCreateSerializer(serializers.Serializer):
    """
    Serializer para crear una nueva reseña.
    
    Aplica validaciones estrictas en la entrada siguiendo Clean Architecture.
    Solo incluye campos que el usuario puede proporcionar.
    """
    hotel_id = serializers.CharField(
        required=True,
        help_text="ID del hotel a reseñar"
    )
    reservation_id = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="ID de la reserva asociada (opcional)"
    )
    rating_breakdown = RatingBreakdownSerializer(required=True)
    title = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        help_text="Título de la reseña"
    )
    comment = serializers.CharField(
        max_length=2000,
        required=True,
        help_text="Comentario detallado (requerido)"
    )
    pros = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        allow_empty=True,
        help_text="Aspectos positivos"
    )
    cons = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        allow_empty=True,
        help_text="Aspectos negativos"
    )
    images = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=True,
        max_length=10,  # Máximo 10 imágenes
        help_text="URLs de imágenes (máx. 10)"
    )
    
    def validate_comment(self, value):
        """Valida que el comentario tenga un mínimo de caracteres."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "El comentario debe tener al menos 10 caracteres"
            )
        return value.strip()
    
    def validate_rating_breakdown(self, value):
        """Valida que al menos una categoría tenga calificación."""
        ratings = [v for v in value.values() if v and v > 0]
        if not ratings:
            raise serializers.ValidationError(
                "Debe proporcionar al menos una calificación"
            )
        return value
    
    def validate(self, data):
        """
        Validación a nivel de objeto.
        Calcula el rating general basado en el breakdown.
        """
        rating_breakdown = data.get('rating_breakdown', {})
        
        # Calcular rating promedio usando la lógica del schema (DRY)
        avg_rating = ReviewSchema.calculate_average_rating(rating_breakdown)
        data['rating'] = avg_rating
        
        return data


class ReviewUpdateSerializer(serializers.Serializer):
    """
    Serializer para actualizar una reseña existente.
    Todos los campos son opcionales.
    """
    rating_breakdown = RatingBreakdownSerializer(required=False)
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    comment = serializers.CharField(max_length=2000, required=False)
    pros = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        allow_empty=True
    )
    cons = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False,
        allow_empty=True
    )
    images = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=True,
        max_length=10
    )
    
    def validate_comment(self, value):
        """Valida longitud mínima del comentario si se proporciona."""
        if value and len(value.strip()) < 10:
            raise serializers.ValidationError(
                "El comentario debe tener al menos 10 caracteres"
            )
        return value.strip() if value else value
    
    def validate(self, data):
        """Recalcula el rating si se actualiza el breakdown."""
        if 'rating_breakdown' in data:
            rating_breakdown = data['rating_breakdown']
            avg_rating = ReviewSchema.calculate_average_rating(rating_breakdown)
            data['rating'] = avg_rating
        
        return data


class ReviewListSerializer(serializers.Serializer):
    """
    Serializer optimizado para listado de reseñas.
    Incluye solo campos esenciales para mejorar performance.
    """
    id = serializers.CharField(read_only=True, source='_id')
    hotel_id = serializers.CharField()
    user_id = serializers.CharField()
    rating = serializers.FloatField()
    title = serializers.CharField()
    comment = serializers.CharField()
    verified_stay = serializers.BooleanField()
    helpful_count = serializers.IntegerField()
    has_response = serializers.BooleanField(read_only=True, required=False)
    created_at = serializers.DateTimeField()
    
    # Información del usuario (se agregará en el service)
    user_info = serializers.DictField(read_only=True, required=False)


class ReviewStatsSerializer(serializers.Serializer):
    """
    Serializer para estadísticas de reseñas de un hotel.
    
    Proporciona información agregada útil para análisis.
    """
    hotel_id = serializers.CharField()
    total_reviews = serializers.IntegerField()
    average_rating = serializers.FloatField()
    rating_distribution = serializers.DictField(
        help_text="Distribución de calificaciones (1-5 estrellas)"
    )
    average_breakdown = serializers.DictField(
        help_text="Promedio por categoría"
    )
    verified_stays_count = serializers.IntegerField()
    recent_reviews_count = serializers.IntegerField(
        help_text="Reseñas en los últimos 30 días"
    )


class OwnerResponseSerializer(serializers.Serializer):
    """Serializer para que el propietario responda a una reseña."""
    comment = serializers.CharField(
        max_length=1000,
        required=True,
        help_text="Respuesta del propietario"
    )
    
    def validate_comment(self, value):
        """Valida que la respuesta tenga contenido."""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "La respuesta debe tener al menos 10 caracteres"
            )
        return value.strip()


class MarkHelpfulSerializer(serializers.Serializer):
    """Serializer para marcar una reseña como útil/no útil."""
    helpful = serializers.BooleanField(
        required=True,
        help_text="True para útil, False para no útil"
    )


class ReportReviewSerializer(serializers.Serializer):
    """Serializer para reportar una reseña."""
    reason = serializers.ChoiceField(
        choices=[
            ('spam', 'Spam o contenido no deseado'),
            ('offensive', 'Contenido ofensivo'),
            ('fake', 'Reseña falsa'),
            ('irrelevant', 'Contenido irrelevante'),
            ('other', 'Otro motivo'),
        ],
        required=True,
        help_text="Motivo del reporte"
    )
    details = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Detalles adicionales"
    )
