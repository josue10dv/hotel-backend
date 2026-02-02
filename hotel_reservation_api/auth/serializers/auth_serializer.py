from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personalizado que extiende TokenObtainPairSerializer para personalizar la generación de tokens JWT.
    Devuelve el token de acceso en el cuerpo de la respuesta y prepara el token de actualización para
    almacenamiento seguro en una cookie HTTP-only.
    """

    @classmethod
    def get_token(cls, user):
        """
        Agrega claims personalizados al token JWT.
        
        Args:
            user: Instancia de User para generar el token.
            
        Returns:
            RefreshToken: Token con claims personalizados (username, email).
        """
        token = super().get_token(user)
        token["username"] = user.username
        token["email"] = user.email
        return token

    def validate(self, attrs):
        """
        Valida las credenciales y prepara la respuesta de autenticación.

        Almacena el token de actualización en un atributo de instancia para la configuración de la cookie por la vista.
        Devuelve solo el token de acceso y los datos del usuario en el cuerpo de la respuesta.
        
        Args:
            attrs (dict): Atributos de entrada validados.
            
        Returns:
            dict: Datos de autenticación con token de acceso e información completa del usuario.
        """
        data = super().validate(attrs)
        self.refresh_token = data["refresh"]
        
        # Construir full_name desde first_name y last_name
        full_name = ""
        if self.user.first_name and self.user.last_name:
            full_name = f"{self.user.first_name} {self.user.last_name}".strip()
        elif self.user.first_name:
            full_name = self.user.first_name
        elif self.user.last_name:
            full_name = self.user.last_name
        else:
            full_name = self.user.username

        return {
            "access": data["access"],
            "user": {
                "id": str(self.user.id),
                "username": self.user.username,
                "email": self.user.email,
                "full_name": full_name,
                "user_type": self.user.user_type,
                "is_active": self.user.is_active,
                "date_joined": self.user.date_joined.isoformat(),
            },
        }


class CookieTokenRefreshSerializer(serializers.Serializer):
    """
    Serializer para refrescar el token de acceso usando el token de actualización almacenado en cookie.

    Recupera el token de actualización de una cookie HTTP-only (no del cuerpo de la solicitud) y
    genera un nuevo token de acceso. Con la rotación de tokens habilitada, también genera
    un nuevo token de actualización.
    """

    def validate(self, attrs):
        """
        Valida el token de actualización y genera un nuevo token de acceso.

        El token de actualización se obtiene del contexto (pasado desde la vista).
        Si ROTATE_REFRESH_TOKENS está habilitado, también genera un nuevo token de actualización.
        
        Args:
            attrs (dict): Atributos de entrada validados (diccionario vacío).
            
        Returns:
            dict: Nuevo token de acceso y opcionalmente nuevo token de actualización.
            
        Raises:
            ValidationError: Si el token de actualización falta o es inválido.
        """
        refresh = self.context.get("refresh_token")

        if not refresh:
            raise serializers.ValidationError(
                "Token de refresco no encontrado en la cookie."
            )

        try:
            refresh_token = RefreshToken(refresh)
            data = {"access": str(refresh_token.access_token)}

            # If token rotation is configured
            if hasattr(refresh_token, "blacklist"):
                refresh_token.blacklist()
                new_refresh = RefreshToken.for_user(refresh_token.user)
                data["refresh"] = str(new_refresh)

            return data

        except TokenError as e:
            raise serializers.ValidationError(f"Token inválido: {str(e)}")

class LogoutSerializer(serializers.Serializer):
    """
    Serializer para el cierre de sesión del usuario.

    Recupera el token de actualización de la cookie y lo agrega a la lista negra
    para invalidarlo permanentemente.
    """

    def validate(self, attrs):
        """
        Valida que el token de actualización exista en la cookie.
        
        Args:
            attrs (dict): Atributos de entrada validados (diccionario vacío).
            
        Returns:
            dict: Atributos validados.
            
        Raises:
            ValidationError: Si el token de actualización no se encuentra en la cookie.
        """
        self.token = self.context.get("refresh_token")

        if not self.token:
            raise serializers.ValidationError(
                "Token de refresco no encontrado en la cookie."
            )

        return attrs

    def save(self, **kwargs):
        """
        Invalida el token de actualización agregándolo a la lista negra.

        El token queda permanentemente invalidado y no puede usarse
        para generar nuevos tokens de acceso.
        """
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except TokenError as e:
            raise serializers.ValidationError(f"Token inválido: {str(e)}")