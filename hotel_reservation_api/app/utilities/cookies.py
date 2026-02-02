"""
Gestión de cookies para tokens de actualización JWT en la API de reservas de hotel.
Este módulo centraliza la configuración y manipulación de cookies, asegurando
consistencia y seguridad en todos los endpoints de autenticación.
"""
from django.conf import settings
from rest_framework.response import Response


def set_refresh_token_cookie(response: Response, refresh_token: str) -> Response:
    """
    Agrega una cookie HTTP-only segura con el token de actualización JWT al objeto Response.

    Esta función centraliza la configuración de cookies, asegurando configuraciones
    de seguridad consistentes en todos los endpoints de autenticación.

    Args:
        response: Objeto Response de DRF al que se adjuntará la cookie.
        refresh_token: Cadena del token JWT de actualización para almacenar.

    Returns:
        Response: El mismo objeto Response con la cookie adjunta.

    Example:
        >>> response = Response(data, status=200)
        >>> response = set_refresh_token_cookie(response, refresh_token)
    """
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_COOKIE_MAX_AGE,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        httponly=settings.REFRESH_TOKEN_COOKIE_HTTPONLY,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
    )
    return response


def delete_refresh_token_cookie(response: Response) -> Response:
    """
    Elimina la cookie del token de actualización JWT del cliente.

    Args:
        response: Objeto Response de DRF al que se adjuntará la eliminación de la cookie.

    Returns:
        Response: El mismo objeto Response con la eliminación de la cookie adjunta.

    Example:
        >>> response = Response({'message': 'Sesión cerrada'}, status=200)
        >>> response = delete_refresh_token_cookie(response)
    """
    response.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
    )
    return response


def get_refresh_token_from_cookie(request) -> str:
    """
    Recupera el token de actualización de las cookies de la solicitud.

    Args:
        request: Objeto Request de DRF.

    Returns:
        str: Cadena del token de actualización o cadena vacía si no se encuentra.

    Example:
        >>> token = get_refresh_token_from_cookie(request)
        >>> if not token:
        >>>     return error_response('No se encontró token de actualización')
    """
    return request.COOKIES.get(settings.REFRESH_TOKEN_COOKIE_NAME, '')
