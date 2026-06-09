"""
PROXVEL Backend - Response Builder.
Genera respuestas JSON estandarizadas para todos los endpoints.
"""

from typing import Any


def success_response(
    data: Any,
    message: str = "Operación exitosa",
    count: int | None = None,
) -> dict:
    """Construye una respuesta exitosa estandarizada."""
    response = {
        "success": True,
        "message": message,
        "data": data,
    }
    if count is not None:
        response["count"] = count
    elif isinstance(data, list):
        response["count"] = len(data)
    return response


def error_response(
    message: str = "Error interno del servidor",
    detail: str | None = None,
) -> dict:
    """Construye una respuesta de error estandarizada."""
    response = {
        "success": False,
        "message": message,
        "data": None,
    }
    if detail:
        response["detail"] = detail
    return response
