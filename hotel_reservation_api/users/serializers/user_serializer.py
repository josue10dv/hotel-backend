from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer para el registro de nuevos usuarios.
    
    Valida y crea usuarios con username, email y contraseña.
    Incluye validaciones de unicidad y confirmación de contraseña.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "password_confirm", "user_type")
        extra_kwargs = {"username": {"required": True}, "email": {"required": True}}

    def validate_email(self, value):
        """Valida que el email sea único en el sistema."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Ya existe un usuario con este email."
            )
        return value

    def validate_username(self, value):
        """Valida que el nombre de usuario sea único en el sistema."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "Ya existe un usuario con este nombre de usuario."
            )
        return value

    def validate(self, attrs):
        """Valida que ambas contraseñas coincidan."""
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password": "Las contraseñas no coinciden."}
            )
        return attrs

    def create(self, validated_data):
        """
        Crea y retorna una nueva instancia de usuario con contraseña encriptada.
        
        Utiliza create_user() para asegurar el hash correcto de la contraseña.
        """
        validated_data.pop("password_confirm")

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )

        return user


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para listar y obtener detalles de usuarios.
    
    Excluye información sensible como contraseñas.
    Campos de solo lectura: id, date_joined.
    """

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "user_type",
            "date_joined",
            "is_active",
        )
        read_only_fields = ("id", "date_joined")


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para actualizar información de usuarios.
    
    Permite actualizar: username, email, first_name, last_name.
    Valida unicidad de email y username excluyendo el usuario actual.
    """

    email = serializers.EmailField(required=False)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "user_type")

    def validate_email(self, value):
        """
        Valida que el email sea único, excluyendo el usuario actual.
        """
        user = self.instance
        if User.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError(
                "Ya existe un usuario con este email."
            )
        return value

    def validate_username(self, value):
        """
        Valida que el nombre de usuario sea único, excluyendo el usuario actual.
        """
        user = self.instance
        if User.objects.filter(username=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError(
                "Ya existe un usuario con este nombre de usuario."
            )
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer para cambio de contraseña de usuario.
    
    Requiere: contraseña actual, nueva contraseña y confirmación.
    Valida que la contraseña actual sea correcta y que las nuevas coincidan.
    """

    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True, write_only=True, validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        """Valida que la contraseña actual sea correcta."""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contraseña actual es incorrecta.")
        return value

    def validate(self, attrs):
        """Valida que ambas contraseñas nuevas coincidan."""
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password": "Las contraseñas nuevas no coinciden."}
            )
        return attrs

    def save(self, **kwargs):
        """Actualiza la contraseña del usuario."""
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user
