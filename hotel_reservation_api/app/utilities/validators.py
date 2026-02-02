"""
Validaciones reutilizables para la API de reservas de hotel.
Este módulo centraliza las validaciones comunes, asegurando consistencia
y reduciendo la duplicación de código en múltiples vistas.
"""
from datetime import datetime
from typing import Optional, Tuple
from rest_framework.response import Response
from rest_framework import status


def parse_datetime_param(
    param_value: Optional[str],
    param_name: str = 'date'
) -> Tuple[Optional[datetime], Optional[Response]]:
    """
    Convierte un parámetro de cadena de fecha y hora en un objeto datetime.

    Args:
        param_value: Cadena de fecha y hora a convertir (formato ISO 8601).
        param_name: Nombre del parámetro para mensajes de error.

    Returns:
        tuple: (parsed_datetime, error_response)
            - En caso de exito: (datetime_object, None)
            - En caso de error: (None, Response_with_error)

    Example:
        >>> from_date, error = parse_datetime_param(request.query_params.get('from_date'), 'from_date')
        >>> if error:
        >>>     return error
    """
    if not param_value:
        return None, None
    
    try:
        parsed_date = datetime.fromisoformat(param_value)
        return parsed_date, None
    except ValueError:
        error_response = Response(
            {'error': f'Formato inválido para {param_name}. Use el formato ISO 8601 (YYYY-MM-DDTHH:MM:SS).'},
            status=status.HTTP_400_BAD_REQUEST
        )
        return None, error_response


def validate_date_range(
    start_date: datetime,
    end_date: datetime
) -> Optional[Response]:
    """
    Valida que la fecha de inicio sea anterior a la fecha de fin.

    Args:
        start_date: Fecha de inicio del rango.
        end_date: Fecha de fin del rango.

    Returns:
        Response: Respuesta de error si la validación falla.
        None: Si la validación es exitosa.

    Example:
        >>> error = validate_date_range(check_in, check_out)
        >>> if error:
        >>>     return error
    """
    if start_date >= end_date:
        return Response(
            {'error': 'La fecha de inicio debe ser anterior a la fecha de fin'},
            status=status.HTTP_400_BAD_REQUEST
        )
    return None


def parse_pagination_params(query_params, default_page_size: int = 20, max_page_size: int = 100) -> dict:
    """
    Parsea los parámetros de paginación de los query params.

    Args:
        query_params: Parámetros de consulta de la solicitud.
        default_page_size: Tamaño de página predeterminado si no se especifica.
        max_page_size: Tamaño máximo permitido para la página.

    Returns:
        dict: Diccionario con los valores de 'page', 'page_size' y 'skip'.

    Example:
        >>> pagination = parse_pagination_params(request.query_params)
        >>> # Returns: {'page': 1, 'page_size': 20, 'skip': 0}
    """
    page = int(query_params.get('page', 1))
    page_size = min(int(query_params.get('page_size', default_page_size)), max_page_size)
    skip = (page - 1) * page_size
    
    return {
        'page': page,
        'page_size': page_size,
        'skip': skip
    }


def extract_filters_from_params(query_params, allowed_filters: list) -> dict:
    """
    Extrae filtros activos de los parámetros de consulta basados en una lista de filtros permitidos.

    Args:
        query_params: Parámetros de consulta de la solicitud.
        allowed_filters: Lista de nombres de campos de filtro permitidos.
    Returns:
        dict: Diccionario de filtros activos.

    Example:
        >>> filters = extract_filters_from_params(
        ...     request.query_params,
        ...     ['status', 'city', 'country']
        ... )
    """
    filters = {}
    for filter_name in allowed_filters:
        if query_params.get(filter_name):
            filters[filter_name] = query_params.get(filter_name)
    return filters
