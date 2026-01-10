from django.urls import path, include
from rest_framework.routers import DefaultRouter
from users.views import UserViewSet

# Router para generar automáticamente las rutas del ViewSet
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

# Endpoints generados automáticamente por el router:
# POST   /api/users/                       → Registrar nuevo usuario (público)
# GET    /api/users/                       → Listar todos los usuarios (autenticado)
# GET    /api/users/{id}/                  → Obtener usuario específico (autenticado)
# GET    /api/users/me/                    → Obtener usuario actual (autenticado)
# PUT    /api/users/{id}/                  → Actualizar usuario completo (autenticado)
# PATCH  /api/users/{id}/                  → Actualizar usuario parcial (autenticado)
# DELETE /api/users/{id}/                  → Desactivar usuario (autenticado)
# POST   /api/users/{id}/change-password/  → Cambiar contraseña (autenticado)

urlpatterns = [
    path("", include(router.urls)),
]
