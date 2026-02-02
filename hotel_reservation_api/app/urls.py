"""
URL configuration for hotel_reservation_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from app.views import health_check, ready_check, live_check

urlpatterns = [
    path('admin/', admin.site.urls),
    # Salud del sistema
    path('health/', health_check, name='health-check'),
    path('ready/', ready_check, name='ready-check'),
    path('live/', live_check, name='live-check'),
    # Rutas de apis
    path('api/', include('users.urls')),
    path('api/auth/', include('auth.urls')),
    path('api/', include('hotels.urls')),
    path('api/', include('reservations.urls')),
    path('api/', include('payments.urls')),
]
