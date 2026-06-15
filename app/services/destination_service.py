"""
PROXVEL Backend - Destination Service.
Lógica de negocio para destinos turísticos.
"""

from typing import Any

from app.repositories import db_destination_repository as destination_repository
from app.schemas.destination_schema import DestinationDetail, DestinationSummary
from sqlalchemy.orm import Session

def get_destinations(db: Session, city: str | None = None, limit: int = 50) -> list[DestinationSummary]:
    """Obtiene lista de destinos filtrada y mapeada al schema de resumen."""
    raw_destinations = destination_repository.get_all_destinations(city=city, limit=limit)
    return [DestinationSummary(**dest) for dest in raw_destinations]

def get_destination_detail(
    db: Session,
    destination_id: str,
    month: int | None = None,
) -> DestinationDetail | None:
    """Obtiene el detalle completo de un destino mapeado al schema detallado."""
    raw_detail = destination_repository.get_destination_by_id(destination_id, month=month)
    return DestinationDetail(**raw_detail) if raw_detail else None
