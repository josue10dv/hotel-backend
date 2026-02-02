"""
Funciones utilitarias para verificar permisos de usuario en vistas de la API.
Estas funciones centralizan patrones comunes de verificación de permisos,
permitiendo reutilización y consistencia en las respuestas de error.
"""
from typing import Optional
from rest_framework.response import Response
from rest_framework import status


def check_is_owner_or_staff(request_user, resource_owner_id: str) -> Optional[Response]:
    """
    Valida si el usuario solicitante es el propietario del recurso o tiene privilegios de staff.

    Args:
        request_user: El usuario que realiza la solicitud (desde request.user).
        resource_owner_id: El ID del propietario del recurso para verificar.

    Returns:
        Response: Respuesta de error con estado 403 si no está autorizado.
        None: Si el usuario está autorizado.

    Example:
        >>> error = check_is_owner_or_staff(request.user, user.id)
        >>> if error:
        >>>     return error
    """
    if str(request_user.id) != str(resource_owner_id) and not request_user.is_staff:
        return Response(
            {'error': 'Solo puedes modificar tus propios recursos o ser staff para hacerlo'},
            status=status.HTTP_403_FORBIDDEN
        )
    return None


def check_is_owner(request_user, resource_owner_id: str, error_message: Optional[str] = None) -> Optional[Response]:
    """
    Valida si el usuario solicitante es el propietario del recurso (verificación estricta).

    A diferencia de check_is_owner_or_staff, esta no permite la anulación por parte del staff.

    Args:
        request_user: El usuario que realiza la solicitud (desde request.user).
        resource_owner_id: El ID del propietario del recurso para verificar.
        error_message: Mensaje de error personalizado (opcional).

    Returns:
        Response: Respuesta de error con estado 403 si no está autorizado.
        None: Si el usuario está autorizado.

    Example:
        >>> error = check_is_owner(request.user, password_owner_id, 
        ...                        'Solo puedes cambiar tu propia contraseña')
        >>> if error:
        >>>     return error
    """
    if str(request_user.id) != str(resource_owner_id):
        message = error_message or 'No tienes permiso para realizar esta acción'
        return Response(
            {'error': message},
            status=status.HTTP_403_FORBIDDEN
        )
    return None


def check_user_type(user, required_type: str, error_message: Optional[str] = None) -> Optional[Response]:
    """
    Valida si el usuario tiene el tipo de usuario requerido.

    Args:
        user: El usuario a verificar.
        required_type: El valor requerido de user_type.
        error_message: Mensaje de error personalizado (opcional).

    Returns:
        Response: Respuesta de error con estado 403 si el tipo de usuario es incorrecto.
        None: Si el usuario tiene el tipo correcto.

    Example:
        >>> error = check_user_type(request.user, 'guest', 
        ...                         'Solo los huéspedes pueden crear reservas')
        >>> if error:
        >>>     return error
    """
    if not hasattr(user, 'user_type') or user.user_type != required_type:
        message = error_message or f'Esta acción requiere el tipo de usuario: {required_type}'
        return Response(
            {'error': message},
            status=status.HTTP_403_FORBIDDEN
        )
    return None
