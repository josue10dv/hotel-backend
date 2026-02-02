from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from auth.serializers import (
    CustomTokenObtainPairSerializer,
    CookieTokenRefreshSerializer,
    LogoutSerializer,
)
from app.utilities import (
    error_response,
    validation_error_response,
    success_response,
    set_refresh_token_cookie,
    delete_refresh_token_cookie,
    get_refresh_token_from_cookie,
)


class LoginView(APIView):
    """
    Autentica usuarios y emite tokens JWT.

    Valida credenciales y retorna:
    - Token de acceso en el cuerpo de la respuesta
    - Token de actualización en cookie HTTP-only segura

    Endpoint: POST /api/auth/login/

    Body de la petición:
        {
            "username": "string",
            "password": "string"
        }

    Respuesta (200):
        {
            "access": "jwt_token",
            "user": {
                "id": "uuid",
                "username": "string",
                "email": "string",
                ...
            }
        }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Autentica al usuario y retorna tokens JWT."""
        serializer = CustomTokenObtainPairSerializer(data=request.data)

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        data = serializer.validated_data
        response = success_response(data=data)
        
        # Establecer token de actualización en cookie segura
        return set_refresh_token_cookie(response, serializer.refresh_token)


class RefreshTokenView(APIView):
    """
    Refresca el token de acceso usando el token de actualización de la cookie.

    Valida el token de actualización de la cookie HTTP-only y genera un nuevo
    token de acceso. Con rotación de tokens habilitada, también emite nuevo token de actualización.

    Endpoint: POST /api/auth/refresh/

    Respuesta (200):
        {
            "access": "new_jwt_token"
        }
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Genera nuevo token de acceso usando el token de actualización de la cookie."""
        refresh_token = get_refresh_token_from_cookie(request)

        if not refresh_token:
            return error_response(
                'Token de actualización no encontrado en cookie',
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        serializer = CookieTokenRefreshSerializer(
            data={}, context={'refresh_token': refresh_token}
        )

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        data = serializer.validated_data
        response = success_response(data={'access': data['access']})

        # Actualizar cookie con nuevo token de actualización si la rotación está habilitada
        if 'refresh' in data:
            return set_refresh_token_cookie(response, data['refresh'])

        return response


class LogoutView(APIView):
    """
    Cierra sesión del usuario invalidando el token de actualización.

    Agrega el token de actualización a la lista negra y elimina la cookie del navegador.
    Nota: El token de acceso permanece válido hasta su expiración natural.

    Endpoint: POST /api/auth/logout/

    Respuesta (205):
        {
            "message": "Successfully logged out"
        }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Invalida el token de actualización y elimina la cookie."""
        refresh_token = get_refresh_token_from_cookie(request)

        if not refresh_token:
            return error_response('No se encontró sesión activa')

        serializer = LogoutSerializer(
            data={}, context={'refresh_token': refresh_token}
        )

        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        serializer.save()
        response = success_response(
            message='Sesión cerrada exitosamente',
            status_code=status.HTTP_205_RESET_CONTENT
        )

        # Remove cookie from browser
        return delete_refresh_token_cookie(response)
