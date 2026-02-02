from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model

User = get_user_model()
from users.serializers import (
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    UserRegistrationSerializer,
)
from app.utilities import (
    success_response,
    created_response,
    validation_error_response,
    list_response,
    check_is_owner_or_staff,
    check_is_owner,
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operaciones CRUD completas sobre el modelo User.

    Endpoints disponibles:
    - POST /api/users/                       → Registrar nuevo usuario (público)
    - GET /api/users/                        → Listar todos los usuarios (autenticado)
    - GET /api/users/{id}/                   → Obtener usuario específico
    - GET /api/users/me/                     → Obtener usuario actual
    - PUT /api/users/{id}/                   → Actualización completa de usuario
    - PATCH /api/users/{id}/                 → Actualización parcial de usuario
    - DELETE /api/users/{id}/                → Desactivar usuario
    - POST /api/users/{id}/change-password/  → Cambiar contraseña
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Retorna el serializador apropiado según la acción."""
        if self.action == "create":
            return UserRegistrationSerializer
        elif self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        elif self.action == "change_password":
            return ChangePasswordSerializer
        return UserSerializer

    def get_permissions(self):
        """Retorna permisos personalizados según la acción."""
        if self.action == "create":
            return [AllowAny()]  # Registro público
        return [IsAuthenticated()]  # El resto requiere autenticación
    
    def create(self, request):
        """
        Registra un nuevo usuario en el sistema.

        Body de la petición:
            {
                "username": "string",
                "email": "string",
                "password": "string",
                "password_confirm": "string"
            }
        """
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        user = serializer.save()
        return created_response(
            data={
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            message='User registered successfully'
        )
    
    def list(self, request):
        """Lista todos los usuarios en el sistema."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return list_response(serializer.data, count=queryset.count())

    def retrieve(self, request, pk=None):
        """Obtiene los detalles de un usuario específico por ID."""
        user = self.get_object()
        serializer = self.get_serializer(user)
        return success_response(data=serializer.data)
    
    def update(self, request, pk=None):
        """Actualiza completamente un usuario (PUT)."""
        user = self.get_object()

        # Verificar permisos: solo el propietario o staff puede actualizar
        permission_error = check_is_owner_or_staff(request.user, user.id)
        if permission_error:
            return permission_error
        
        serializer = self.get_serializer(user, data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        serializer.save()
        return success_response(
            data=serializer.data,
            message='Usuario actualizado exitosamente'
        )
    
    def partial_update(self, request, pk=None):
        """Actualiza parcialmente un usuario (PATCH)."""
        user = self.get_object()

        # Verificar permisos: solo el propietario o staff puede actualizar
        permission_error = check_is_owner_or_staff(request.user, user.id)
        if permission_error:
            return permission_error
        
        serializer = self.get_serializer(user, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        serializer.save()
        return success_response(
            data=serializer.data,
            message='Usuario actualizado exitosamente'
        )
    
    def destroy(self, request, pk=None):
        """
        Elimina lógicamente un usuario desactivando la cuenta.

        No elimina físicamente el registro, solo lo desactiva.
        """
        user = self.get_object()

        # Verificar permisos: solo el propietario o staff puede eliminar
        permission_error = check_is_owner_or_staff(request.user, user.id)
        if permission_error:
            return permission_error

        # Eliminación lógica: desactivar en lugar de eliminar
        user.is_active = False
        user.save()

        return success_response(
            message='Cuenta de usuario desactivada exitosamente',
            status_code=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=["post"], url_path="change-password")
    def change_password(self, request, pk=None):
        """
        Cambia la contraseña del usuario.

        Endpoint: POST /api/users/{id}/change-password/

        Body de la petición:
            {
                "old_password": "string",
                "new_password": "string",
                "new_password_confirm": "string"
            }
        """
        user = self.get_object()

        # Solo el usuario puede cambiar su propia contraseña (verificación estricta)
        permission_error = check_is_owner(
            request.user, 
            user.id, 
            'Solo puedes cambiar tu propia contraseña'
        )
        if permission_error:
            return permission_error

        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
        
        serializer.save()
        return success_response(message='Contraseña cambiada exitosamente')
    
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """
        Obtiene el usuario autenticado actual.

        Endpoint: GET /api/users/me/
        """
        serializer = self.get_serializer(request.user)
        return success_response(data=serializer.data)
