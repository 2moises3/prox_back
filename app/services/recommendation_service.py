"""
PROXVEL Backend - Recommendation Service.
Lógica de negocio para búsqueda y recomendaciones.
"""

from typing import Any

from app.repositories import db_ranking_repository as ranking_repository


def search(
    query: str | None = None,
    city: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Busca destinos por texto o ciudad en los datos de ranking.
    Ordena resultados por compatibilidad descendente.
    """
    return ranking_repository.search_recommendations(
        query=query,
        city=city,
        limit=limit,
    )


def get_base_recommendations() -> dict[str, Any]:
    """
    Endpoint de recomendaciones base (Fase 3).
    Actualmente queda como stub documentado porque el archivo
    específico de afinidad destino-perfil (Fase 3 pura) puede
    no existir de forma independiente.

    Los datos de Fase 3 ya están parcialmente incluidos en
    ranking_contextual_final.csv (columna score_fase3).
    """
    return {
        "message": (
            "Endpoint preparado. Las recomendaciones base de Fase 3 "
            "están parcialmente disponibles a través del ranking contextual "
            "(campo score_fase3). Un archivo independiente de Fase 3 "
            "podrá integrarse en una versión futura."
        ),
        "data": [],
        "partially_available_via": "/api/v1/recommendations/contextual",
    }
