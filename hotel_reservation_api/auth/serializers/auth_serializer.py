from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personalizado para autenticación de usuarios.

    Hereda de TokenObtainPairSerializer para customizar la generación de tokens JWT.
    Retorna access token en el body y prepara refresh token para cookie segura.
    """

    @classmethod
    def get_token(cls, user):
        """Agrega claims personalizados (username, email) al payload del token JWT."""
        token = super().get_token(user)
        token["username"] = user.username
        token["email"] = user.email
        return token

    def validate(self, attrs):
        """
        Valida credenciales y prepara la respuesta de autenticación.

        Guarda el refresh token en un atributo para que la vista lo establezca en cookie.
        Retorna solo el access token y datos del usuario en el body.
        """
        data = super().validate(attrs)
        self.refresh_token = data["refresh"]

        return {
            "access": data["access"],
            "user": {
                "id": self.user.id,
                "username": self.user.username,
                "email": self.user.email,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
            },
        }


class CookieTokenRefreshSerializer(serializers.Serializer):
    """
    Serializer para refrescar el access token usando refresh token de cookie.

    Obtiene el refresh token desde cookie HttpOnly (no del body) y genera
    un nuevo access token. Si hay rotación habilitada, genera nuevo refresh token.
    """

    def validate(self, attrs):
        """
        Valida el refresh token y genera nuevo access token.

        El refresh token se obtiene del contexto (pasado desde la vista).
        Si ROTATE_REFRESH_TOKENS está habilitado, también genera nuevo refresh token.
        """
        refresh = self.context.get("refresh_token")

        if not refresh:
            raise serializers.ValidationError(
                "Refresh token no encontrado en la cookie."
            )

        try:
            refresh_token = RefreshToken(refresh)
            data = {"access": str(refresh_token.access_token)}

            # Si hay rotación de tokens configurada
            if hasattr(refresh_token, "blacklist"):
                refresh_token.blacklist()
                new_refresh = RefreshToken.for_user(refresh_token.user)
                data["refresh"] = str(new_refresh)

            return data

        except TokenError as e:
            raise serializers.ValidationError(f"Token inválido: {str(e)}")


class LogoutSerializer(serializers.Serializer):
    """
    Serializer para cerrar sesión (logout).

    Obtiene el refresh token de la cookie y lo agrega a la blacklist
    para invalidarlo permanentemente.
    """

    def validate(self, attrs):
        """Valida que exista un refresh token en la cookie."""
        self.token = self.context.get("refresh_token")

        if not self.token:
            raise serializers.ValidationError(
                "Refresh token no encontrado en la cookie."
            )

        return attrs

    def save(self, **kwargs):
        """
        Invalida el refresh token agregándolo a la blacklist.

        El token queda permanentemente invalidado y no puede usarse
        para generar nuevos access tokens.
        """
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except TokenError as e:
            raise serializers.ValidationError(f"Token inválido: {str(e)}")