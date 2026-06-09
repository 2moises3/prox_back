"""
PROXVEL Backend - Tourism Service.
Lógica de negocio para el catálogo turístico oficial.
Solo expone información complementaria; no modifica scores de tesis.
"""

from typing import Any

from app.repositories import db_tourism_repository as tourism_repository


def get_catalog() -> list[dict[str, Any]]:
    """Obtiene la lista completa del catálogo turístico."""
    return tourism_repository.get_all_catalog()


def get_catalog_detail(destination_id: str) -> dict[str, Any] | None:
    """Obtiene el detalle turístico de un destino."""
    return tourism_repository.get_catalog_by_id(destination_id)


def get_map_markers() -> list[dict[str, Any]]:
    """Obtiene marcadores de mapa con coordenadas válidas."""
    return tourism_repository.get_map_markers()


def get_enrichment(destination_id: str) -> dict[str, Any] | None:
    """
    Obtiene datos de enriquecimiento del catálogo para un destino.
    Se usa para enriquecer endpoints de destinations y recommendations.
    """
    return tourism_repository.get_enrichment_data(destination_id)
