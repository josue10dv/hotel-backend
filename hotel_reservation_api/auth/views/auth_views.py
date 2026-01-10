from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings
from auth.serializers import (
    CustomTokenObtainPairSerializer,
    CookieTokenRefreshSerializer,
    LogoutSerializer,
)


class LoginView(APIView):
    """
    Vista para autenticación de usuarios (login).

    Valida credenciales, genera tokens JWT y establece:
    - Access token en el body de la respuesta
    - Refresh token en cookie HttpOnly segura

    Endpoint: POST /api/auth/login/
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """
        Autentica al usuario y retorna tokens.

        Payload esperado:
        {
            "username": "string",
            "password": "string"
        }
        """
        serializer = CustomTokenObtainPairSerializer(data=request.data)

        if serializer.is_valid():
            data = serializer.validated_data
            response = Response(data, status=status.HTTP_200_OK)

            # Establecer refresh token en cookie segura
            response.set_cookie(
                key=settings.REFRESH_TOKEN_COOKIE_NAME,
                value=serializer.refresh_token,
                max_age=settings.REFRESH_TOKEN_COOKIE_MAX_AGE,
                secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
                httponly=settings.REFRESH_TOKEN_COOKIE_HTTPONLY,
                samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
            )

            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RefreshTokenView(APIView):
    """
    Vista para refrescar el access token.

    Obtiene el refresh token de la cookie, valida que no esté en blacklist
    y genera un nuevo access token. Si hay rotación habilitada, también
    genera un nuevo refresh token.

    Endpoint: POST /api/auth/refresh/
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Genera un nuevo access token usando el refresh token de la cookie."""
        refresh_token = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)

        if not refresh_token:
            return Response(
                {"error": "Refresh token no encontrado en cookie."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = CookieTokenRefreshSerializer(
            data={}, context={"refresh_token": refresh_token}
        )

        if serializer.is_valid():
            data = serializer.validated_data
            response = Response({"access": data["access"]}, status=status.HTTP_200_OK)

            # Si hay rotación de tokens, actualizar cookie con nuevo refresh
            if "refresh" in data:
                response.set_cookie(
                    key=settings.REFRESH_TOKEN_COOKIE_NAME,
                    value=data["refresh"],
                    max_age=settings.REFRESH_TOKEN_COOKIE_MAX_AGE,
                    secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
                    httponly=settings.REFRESH_TOKEN_COOKIE_HTTPONLY,
                    samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
                )

            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    Vista para cerrar sesión (logout).

    Invalida el refresh token agregándolo a la blacklist y elimina
    la cookie del navegador. El access token actual sigue válido hasta
    su expiración natural.

    Endpoint: POST /api/auth/logout/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Cierra la sesión del usuario invalidando el refresh token.

        Agrega el refresh token a la blacklist para prevenir la generación
        de nuevos access tokens.
        """
        refresh_token = request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME)

        if not refresh_token:
            return Response(
                {"error": "No hay sesión activa."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LogoutSerializer(data={}, context={"refresh_token": refresh_token})

        if serializer.is_valid():
            serializer.save()
            response = Response(
                {"message": "Logout exitoso."}, status=status.HTTP_205_RESET_CONTENT
            )

            # Eliminar cookie del navegador
            response.delete_cookie(
                key=settings.REFRESH_TOKEN_COOKIE_NAME,
                samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
            )

            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
