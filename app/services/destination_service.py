"""
PROXVEL Backend - Destination Service.
Lógica de negocio para destinos turísticos.
"""

from typing import Any

from app.repositories import db_destination_repository as destination_repository


def get_destinations(
    city: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Obtiene lista de destinos con filtros opcionales."""
    return destination_repository.get_all_destinations(city=city, limit=limit)


def get_destination_detail(destination_id: str) -> dict[str, Any] | None:
    """Obtiene el detalle completo de un destino por su ID."""
    return destination_repository.get_destination_by_id(destination_id)
