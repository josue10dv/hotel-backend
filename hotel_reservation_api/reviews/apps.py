"""
Configuración de la aplicación Reviews.
"""
from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    """Configuración para el módulo de reseñas."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reviews'
    verbose_name = 'Reseñas de Hoteles'
