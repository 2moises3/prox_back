"""
PROXVEL Backend - Contextual Ranking Service.
Lógica de negocio para ranking contextual (Fase 4).
"""

from typing import Any

from app.repositories import db_ranking_repository as ranking_repository


def get_contextual_ranking(
    user_id: str | None = None,
    city: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Obtiene el ranking contextual final.
    Delega al repository para acceso a datos y filtrado.
    """
    return ranking_repository.get_contextual_ranking(
        user_id=user_id,
        city=city,
        limit=limit,
    )
