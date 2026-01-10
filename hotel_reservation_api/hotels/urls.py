"""
URLs para la app de hoteles.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from hotels.views import HotelViewSet

# Crear router para el ViewSet
router = DefaultRouter()
router.register(r'hotels', HotelViewSet, basename='hotel')

urlpatterns = [
    path('', include(router.urls)),
]
