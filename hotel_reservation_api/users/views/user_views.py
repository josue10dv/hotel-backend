from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model

User = get_user_model()
from users.serializers import (
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    UserRegistrationSerializer,
)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operaciones CRUD completas del modelo User.

    Endpoints disponibles:
    - POST /api/users/                       → Registrar nuevo usuario (público)
    - GET /api/users/                        → Listar todos los usuarios (autenticado)
    - GET /api/users/{id}/                   → Obtener usuario específico
    - GET /api/users/me/                     → Obtener usuario actual
    - PUT /api/users/{id}/                   → Actualizar usuario completo
    - PATCH /api/users/{id}/                 → Actualizar usuario parcial
    - DELETE /api/users/{id}/                → Desactivar usuario
    - POST /api/users/{id}/change-password/  → Cambiar contraseña
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Retorna el serializer apropiado según la acción."""
        if self.action == "create":
            return UserRegistrationSerializer
        elif self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        elif self.action == "change_password":
            return ChangePasswordSerializer
        return UserSerializer

    def get_permissions(self):
        """Retorna los permisos personalizados según la acción."""
        if self.action == "create":
            return [AllowAny()]  # Registro público
        return [IsAuthenticated()]  # Resto requiere autenticación
    
    def create(self, request):
        """
        Registra un nuevo usuario en el sistema.

        Payload esperado:
        {
            "username": "string",
            "email": "string",
            "password": "string",
            "password_confirm": "string"
        }
        """
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "message": "Usuario registrado exitosamente",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def list(self, request):
        """Lista todos los usuarios del sistema."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"count": queryset.count(), "users": serializer.data})

    def retrieve(self, request, pk=None):
        """Obtiene los detalles de un usuario específico por ID."""
        user = self.get_object()
        serializer = self.get_serializer(user)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """Actualiza completamente un usuario (PUT)."""
        user = self.get_object()

        # Solo el propio usuario o un administrador pueden actualizar
        if request.user.id != user.id and not request.user.is_staff:
            return Response(
                {"error": "Solo puedes actualizar tu propio perfil."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        serializer = self.get_serializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Usuario actualizado exitosamente", "user": serializer.data}
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, pk=None):
        """Actualiza parcialmente un usuario (PATCH)."""
        user = self.get_object()

        # Solo el propio usuario o un administrador pueden actualizar
        if request.user.id != user.id and not request.user.is_staff:
            return Response(
                {"error": "Solo puedes actualizar tu propio perfil."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Usuario actualizado exitosamente", "user": serializer.data}
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None):
        """
        Elimina un usuario (soft delete desactivando la cuenta).

        No elimina físicamente el registro, solo desactiva la cuenta.
        """
        user = self.get_object()

        # Solo el propio usuario o un administrador pueden eliminar
        if request.user.id != user.id and not request.user.is_staff:
            return Response(
                {"error": "Solo puedes eliminar tu propia cuenta."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Soft delete: desactivar en lugar de eliminar
        user.is_active = False
        user.save()

        return Response(
            {"message": "Cuenta de usuario desactivada exitosamente."},
            status=status.HTTP_204_NO_CONTENT,
        )
    
    @action(detail=True, methods=["post"], url_path="change-password")
    def change_password(self, request, pk=None):
        """
        Cambia la contraseña del usuario.

        Endpoint: POST /api/users/{id}/change-password/

        Payload esperado:
        {
            "old_password": "string",
            "new_password": "string",
            "new_password_confirm": "string"
        }
        """
        user = self.get_object()

        # Solo el propio usuario puede cambiar su contraseña
        if request.user.id != user.id:
            return Response(
                {"error": "Solo puedes cambiar tu propia contraseña."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Contraseña cambiada exitosamente."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """
        Obtiene el usuario autenticado actual.

        Endpoint: GET /api/users/me/
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
