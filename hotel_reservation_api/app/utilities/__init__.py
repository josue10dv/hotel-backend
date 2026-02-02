"""
Modulo de utilidades para la API de reservas de hotel.
Proporciona funciones reutilizables para respuestas HTTP, permisos,
validaciones y gestión de cookies.
"""

from .responses import (
    success_response,
    error_response,
    validation_error_response,
    not_found_response,
    permission_denied_response,
    created_response,
    list_response,
)
from .permissions import (
    check_is_owner_or_staff,
    check_is_owner,
    check_user_type,
)
from .validators import (
    parse_datetime_param,
    validate_date_range,
    parse_pagination_params,
    extract_filters_from_params,
)
from .cookies import (
    set_refresh_token_cookie,
    delete_refresh_token_cookie,
    get_refresh_token_from_cookie,
)

__all__ = [
    # Response utilities
    success_response,
    error_response,
    validation_error_response,
    not_found_response,
    permission_denied_response,
    created_response,
    list_response,
    # Permission utilities
    check_is_owner_or_staff,
    check_is_owner,
    check_user_type,
    # Validation utilities
    parse_datetime_param,
    validate_date_range,
    parse_pagination_params,
    extract_filters_from_params,
    # Cookie utilities
    set_refresh_token_cookie,
    delete_refresh_token_cookie,
    get_refresh_token_from_cookie,
]
