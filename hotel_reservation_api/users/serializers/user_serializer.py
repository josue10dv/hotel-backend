from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer para el registro de nuevos usuarios.
    
    Valida y crea usuarios con nombre de usuario, correo electrónico y contraseña.
    Incluye validación de unicidad y confirmación de contraseña.
    
    Campos:
        username (str): Nombre de usuario único.
        email (EmailField): Dirección de correo electrónico única.
        password (str): Contraseña que cumple con los requisitos de validación.
        password_confirm (str): Confirmación de contraseña (debe coincidir con password).
        user_type (str): Tipo de cuenta de usuario.
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
        """
        Valida la unicidad del correo electrónico en el sistema.
        
        Args:
            value (str): Dirección de correo electrónico a validar.
            
        Returns:
            str: Dirección de correo electrónico validada.
            
        Raises:
            ValidationError: Si el correo electrónico ya existe.
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value

    def validate_username(self, value):
        """
        Valida la unicidad del nombre de usuario en el sistema.
        
        Args:
            value (str): Nombre de usuario a validar.
            
        Returns:
            str: Nombre de usuario validado.
            
        Raises:
            ValidationError: Si el nombre de usuario ya existe.
        """
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return value

    def validate(self, attrs):
        """
        Valida que ambas contraseñas coincidan.
        
        Args:
            attrs (dict): Todos los valores de los campos.
            
        Returns:
            dict: Atributos validados.
            
        Raises:
            ValidationError: Si las contraseñas no coinciden.
        """
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password": "Las contraseñas no coinciden."}
            )
        return attrs

    def create(self, validated_data):
        """
        Crea y retorna el usuario creado con sus credenciales encriptadas.
        
        Usa create_user() para asegurar el hash correcto de la contraseña.
        
        Args:
            validated_data (dict): Datos validados del usuario.
            
        Returns:
            User: Instancia del usuario creado.
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
    
    Campos:
        id (UUID): Identificador único del usuario (solo lectura).
        username (str): Nombre de usuario.
        email (EmailField): Dirección de correo electrónico.
        first_name (str): Nombre.
        last_name (str): Apellido.
        user_type (str): Tipo de cuenta.
        date_joined (DateTime): Fecha de registro (solo lectura).
        is_active (bool): Estado activo de la cuenta.
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
    Serializer para actualizar información del usuario.
    
    Permite actualizar: nombre de usuario, correo electrónico, nombre, apellido.
    Valida la unicidad del correo electrónico y nombre de usuario excluyendo al usuario actual.
    
    Campos:
        username (str): Nombre de usuario.
        email (EmailField): Dirección de correo electrónico.
        first_name (str): Nombre.
        last_name (str): Apellido.
        user_type (str): Tipo de cuenta.
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
    Serializer para el cambio de contraseña del usuario.
    
    Requiere: contraseña actual, nueva contraseña y confirmación.
    Valida que la contraseña actual sea correcta y que las nuevas contraseñas coincidan.
    
    Campos:
        old_password (str): Contraseña actual para verificación.
        new_password (str): Nueva contraseña (debe cumplir con los requisitos de validación).
        new_password_confirm (str): Confirmación de la nueva contraseña.
    """

    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True, write_only=True, validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        """
        Valida que la contraseña actual sea correcta.
        
        Args:
            value (str): Contraseña actual proporcionada por el usuario.
            
        Returns:
            str: Contraseña validada.
            
        Raises:
            ValidationError: Si la contraseña actual es incorrecta.
        """
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contraseña actual es incorrecta.")
        return value

    def validate(self, attrs):
        """
        Valida que ambas nuevas contraseñas coincidan.
        
        Args:
            attrs (dict): Todos los valores de los campos.
            
        Returns:
            dict: Atributos validados.
            
        Raises:
            ValidationError: Si las nuevas contraseñas no coinciden.
        """
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password": "Las nuevas contraseñas no coinciden."}
            )
        return attrs

    def save(self, **kwargs):
        """
        Actualiza la contraseña del usuario.
        
        Returns:
            User: Instancia de usuario actualizada.
        """
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user
