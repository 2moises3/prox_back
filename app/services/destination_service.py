"""
PROXVEL Backend - Destination Service.
Lógica de negocio para destinos turísticos.
"""

from typing import Any

from app.repositories import db_destination_repository as destination_repository
from app.schemas.destination_schema import DestinationDetail, DestinationSummary
from sqlalchemy.orm import Session

def get_destinations(db: Session, city: str | None = None, limit: int = 50, include_inactive: bool = False) -> list[DestinationSummary]:
    """Obtiene lista de destinos filtrada y mapeada al schema de resumen.

    include_inactive=False (por defecto) oculta destinos inactivos: lo usa el
    catálogo público. El dashboard admin pasa include_inactive=True.
    """
    raw_destinations = destination_repository.get_all_destinations(
        city=city, limit=limit, include_inactive=include_inactive
    )
    return [DestinationSummary(**dest) for dest in raw_destinations]


def set_destination_status(db: Session, destination_id: str, is_active: bool) -> DestinationDetail | None:
    """Activa/desactiva un destino. Devuelve el detalle actualizado o None si no existe."""
    raw_detail = destination_repository.set_destination_status(db, destination_id, is_active)
    return DestinationDetail(**raw_detail) if raw_detail else None

def get_destination_detail(
    db: Session,
    destination_id: str,
    month: int | None = None,
    include_inactive: bool = False
) -> DestinationDetail | None:
    """Obtiene el detalle completo de un destino mapeado al schema detallado."""
    raw_detail = destination_repository.get_destination_by_id(destination_id, month=month, include_inactive=include_inactive)
    return DestinationDetail(**raw_detail) if raw_detail else None

def update_destination_admin(db: Session, destination_id: str, update_data: dict[str, Any]) -> DestinationDetail | None:
    raw_detail = destination_repository.update_destination_admin(db, destination_id, update_data)
    return DestinationDetail(**raw_detail) if raw_detail else None

def create_destination_admin(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    return destination_repository.create_destination_admin(db, data)


def update_absa_scores(db: Session, destination_id: str, scores: dict[str, float | None]) -> DestinationDetail | None:
    """Actualiza los puntajes ABSA de un destino y devuelve el detalle actualizado."""
    destination_repository.upsert_aspect_scores(db, destination_id, scores)
    return get_destination_detail(db, destination_id, include_inactive=True)
