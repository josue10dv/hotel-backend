"""
URLs para notificaciones.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from notifications.views import NotificationViewSet

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

app_name = 'notifications'

urlpatterns = [
    path('', include(router.urls)),
]
