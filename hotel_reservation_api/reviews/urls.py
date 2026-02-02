"""
URLs del módulo de reseñas.
Define las rutas de los endpoints de la API de reviews.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from reviews.views import ReviewViewSet


# Router de DRF para generar URLs automáticamente
router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = [
    path('', include(router.urls)),
]
