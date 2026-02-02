"""
Estandariza las respuestas de la API para todos los endpoints.

Este módulo proporciona funciones auxiliares para crear estructuras de respuesta uniformes
en todos los endpoints de la API, siguiendo principios DRY y mejorando la mantenibilidad.
"""
from rest_framework import status
from rest_framework.response import Response
from typing import Any, Dict, Optional


# Response key constants
KEY_MESSAGE = 'message'
KEY_ERROR = 'error'
KEY_DATA = 'data'
KEY_COUNT = 'count'
KEY_DETAIL = 'detail'


def success_response(
    data: Optional[Any] = None,
    message: Optional[str] = None,
    status_code: int = status.HTTP_200_OK
) -> Response:
    """
    Crea una respuesta de éxito estandarizada.

    Args:
        data: Datos del payload de la respuesta.
        message: Mensaje de éxito opcional.
        status_code: Código de estado HTTP (por defecto: 200).

    Returns:
        Response: Objeto Response de DRF con estructura estandarizada.

    Example:
        >>> success_response(data={'user': user_data}, message='Usuario actualizado exitosamente')
        Response({'message': 'Usuario actualizado exitosamente', 'data': {...}}, status=200)
    """
    response_data = {}
    
    if message:
        response_data[KEY_MESSAGE] = message
    
    if data is not None:
        response_data[KEY_DATA] = data
    
    return Response(response_data, status=status_code)


def error_response(
    error: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    error_code: Optional[str] = None,
    additional_data: Optional[Dict] = None
) -> Response:
    """
    Crea una respuesta de error estandarizada.

    Args:
        error: Mensaje de error que describe qué salió mal.
        status_code: Código de estado HTTP (por defecto: 400).
        error_code: Código de error opcional para el manejo del cliente.
        additional_data: Contexto adicional opcional del error.

    Returns:
        Response: Objeto Response de DRF con estructura de error.

    Example:
        >>> error_response('Credenciales inválidas', status.HTTP_401_UNAUTHORIZED)
        Response({'error': 'Credenciales inválidas'}, status=401)
    """
    response_data = {KEY_ERROR: error}
    
    if error_code:
        response_data['error_code'] = error_code
    
    if additional_data:
        response_data.update(additional_data)
    
    return Response(response_data, status=status_code)


def validation_error_response(errors: Dict) -> Response:
    """
    Crea una respuesta de error de validación estandarizada.

    Args:
        errors: Diccionario de errores de validación a nivel de campo.

    Returns:
        Response: Objeto Response de DRF con errores de validación.

    Example:
        >>> validation_error_response({'email': ['El correo electrónico ya existe']})
        Response({'email': ['El correo electrónico ya existe']}, status=400)
    """
    return Response(errors, status=status.HTTP_400_BAD_REQUEST)


def not_found_response(resource: str = 'Resource') -> Response:
    """
    Crea una respuesta estandarizada de 404 no encontrado.

    Args:
        resource: Nombre del recurso que no fue encontrado.

    Returns:
        Response: Objeto Response de DRF con estado 404.

    Example:
        >>> not_found_response('Usuario')
        Response({'detail': 'Usuario no encontrado'}, status=404)
    """
    return Response(
        {KEY_DETAIL: f'{resource} no encontrado'},
        status=status.HTTP_404_NOT_FOUND
    )


def permission_denied_response(message: str = 'Permiso denegado') -> Response:
    """
    Crea una respuesta estandarizada de 403 permiso denegado.

    Args:
        message: Mensaje personalizado de permiso denegado.

    Returns:
        Response: Objeto Response de DRF con estado 403.

    Example:
        >>> permission_denied_response('Solo los administradores pueden realizar esta acción')
        Response({'error': '...'}, status=403)
    """
    return Response(
        {KEY_ERROR: message},
        status=status.HTTP_403_FORBIDDEN
    )


def created_response(
    data: Any,
    message: str = 'Recurso creado exitosamente'
) -> Response:
    """
    Crea una respuesta estandarizada de recurso creado (201).

    Args:
        data: Datos del recurso creado.
        message: Mensaje de éxito.
    Returns:
        Response: Objeto Response de DRF con estado 201.

    Example:
        >>> created_response(user_data, 'Usuario registrado exitosamente')
        Response({'message': '...', 'data': {...}}, status=201)
    """
    return Response(
        {KEY_MESSAGE: message, KEY_DATA: data},
        status=status.HTTP_201_CREATED
    )


def list_response(
    items: list,
    count: Optional[int] = None,
    **extra_fields
) -> Response:
    """
    Crea una respuesta estandarizada para listas de recursos.

    Args:
        items: Lista de elementos serializados.
        count: Conteo total de elementos (si es diferente de la longitud de items).
        **extra_fields: Campos adicionales como página, tamaño de página, etc.

    Returns:
        Response: Objeto Response de DRF con estructura de lista.

    Example:
        >>> list_response(users, count=100, page=1, page_size=20)
        Response({'count': 100, 'data': [...], 'page': 1, ...}, status=200)
    """
    response_data = {
        KEY_COUNT: count if count is not None else len(items),
        KEY_DATA: items
    }
    response_data.update(extra_fields)
    
    return Response(response_data, status=status.HTTP_200_OK)
