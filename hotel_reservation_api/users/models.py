import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Modelo de usuario personalizado con UUID como clave primaria.

    Extiende AbstractUser de Django para mantener toda la funcionalidad
    estándar (username, email, password, etc.) pero reemplaza el id
    entero auto-incremental por un UUID.
    """
    
    class UserType(models.TextChoices):
        """Tipos de usuario en el sistema."""
        GUEST = "guest"
        OWNER = "owner"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID",
        help_text="Identificador único universal del usuario",
    )
    
    user_type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.GUEST,
        verbose_name="Tipo de usuario",
        help_text="Define si el usuario es propietario de propiedades o consumidor/huésped",
    )

    class Meta:
        db_table = "users_user"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.username} ({self.email})"
    
    def is_owner(self):
        """Verifica si el usuario es propietario."""
        return self.user_type == self.UserType.OWNER
    
    def is_guest(self):
        """Verifica si el usuario es consumidor/huésped."""
        return self.user_type == self.UserType.GUEST
