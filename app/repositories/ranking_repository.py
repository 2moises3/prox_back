"""
PROXVEL Backend - Ranking Repository.
Acceso a datos de ranking contextual final desde CSV.

Fuente: ranking_contextual_final.csv
Columnas clave: user_id, destination, rank, score_fase3,
  compatibilidad, etiqueta_triclase, score_clima, score_aforo,
  score_final_fase4, rank_fase4, compatibilidad_final,
  etiqueta_final, explicacion_final

Enriquecimiento (Fase 1B): datos complementarios del catálogo
turístico (city, region, category, cover_image_url, tourism_summary)
sin modificar scores ni ranking.

# TODO: Migrar a PostgreSQL en fase futura.
"""

import logging
from typing import Any

from app.repositories.csv_loader import get_data
from app.repositories import tourism_repository
from app.utils.normalizers import generate_destination_id, safe_float, safe_int

logger = logging.getLogger(__name__)


def get_contextual_ranking(
    user_id: str | None = None,
    city: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Devuelve el ranking contextual final.
    - Si se proporciona user_id, filtra por usuario.
    - Si no, devuelve una muestra representativa (primer usuario).
    - city: filtra por ciudad usando datos del catálogo (Fase 1B).
    """
    ranking_data = get_data("ranking")
    if ranking_data is None:
        logger.warning("Datos de ranking no disponibles")
        return []

    # Filtrar por usuario
    if user_id:
        filtered = [r for r in ranking_data if r.get("user_id") == user_id]
    else:
        # Sin user_id → devolver del primer usuario como demo
        all_users = sorted(set(r.get("user_id", "") for r in ranking_data))
        first_user = all_users[0] if all_users else None
        filtered = [
            r for r in ranking_data
            if r.get("user_id") == first_user
        ] if first_user else []

    # Ordenar por rank_fase4
    filtered.sort(key=lambda x: safe_int(x.get("rank_fase4"), 9999))

    # Transformar a formato de respuesta
    results = []
    for row in filtered[:limit]:
        item = _build_recommendation_item(row)
        # Enriquecer con catálogo turístico (Fase 1B)
        _enrich_with_catalog(item)
        results.append(item)

    # Filtro por ciudad (ahora funcional con catálogo, Fase 1B)
    if city:
        results = [
            r for r in results
            if r.get("city") and city.lower() in r["city"].lower()
        ]

    return results


def search_recommendations(
    query: str | None = None,
    city: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Búsqueda de destinos por texto en el ranking contextual.
    Busca coincidencias parciales en el nombre del destino.
    Enriquecido con datos del catálogo turístico (Fase 1B).
    """
    ranking_data = get_data("ranking")
    if ranking_data is None:
        logger.warning("Datos de ranking no disponibles")
        return []

    # Obtener registros únicos por destino (tomar mejor ranking)
    seen_destinations: dict[str, dict] = {}
    for row in ranking_data:
        dest = row.get("destination", "")
        dest_id = generate_destination_id(dest)

        if dest_id not in seen_destinations:
            seen_destinations[dest_id] = row
        else:
            # Conservar el que tenga mejor compatibilidad_final
            current_score = safe_float(
                seen_destinations[dest_id].get("compatibilidad_final"), 0
            )
            new_score = safe_float(row.get("compatibilidad_final"), 0)
            if new_score > current_score:
                seen_destinations[dest_id] = row

    unique_rows = list(seen_destinations.values())

    # Filtrar por query (búsqueda por texto en nombre de destino)
    if query:
        query_lower = query.lower()
        unique_rows = [
            r for r in unique_rows
            if query_lower in (r.get("destination", "") or "").lower()
        ]

    # Ordenar por compatibilidad_final descendente
    unique_rows.sort(
        key=lambda x: safe_float(x.get("compatibilidad_final"), 0),
        reverse=True,
    )

    results = []
    for row in unique_rows[:limit]:
        dest_id = generate_destination_id(row.get("destination", ""))
        enrichment = tourism_repository.get_enrichment_data(dest_id)

        item = {
            "destination_id": dest_id,
            "destination": row.get("destination"),
            "city": enrichment.get("city") if enrichment else None,
            "region": enrichment.get("region") if enrichment else None,
            "category": enrichment.get("category") if enrichment else None,
            "cover_image_url": enrichment.get("cover_image_url") if enrichment else None,
            "compatibility_percentage": safe_float(
                row.get("compatibilidad_final")
            ),
            "final_score": safe_float(row.get("score_final_fase4")),
        }
        results.append(item)

    # Filtro por ciudad (Fase 1B)
    if city:
        results = [
            r for r in results
            if r.get("city") and city.lower() in r["city"].lower()
        ]

    return results


def _build_recommendation_item(row: dict[str, Any]) -> dict[str, Any]:
    """Transforma una fila de ranking CSV al formato RecommendationItem."""
    return {
        "rank": safe_int(row.get("rank_fase4")),
        "destination_id": generate_destination_id(
            row.get("destination", "")
        ),
        "destination": row.get("destination"),
        "city": None,
        "region": None,
        "category": None,
        "cover_image_url": None,
        "compatibility_percentage": safe_float(
            row.get("compatibilidad_final")
        ),
        "label": row.get("etiqueta_final"),
        "final_score": safe_float(row.get("score_final_fase4")),
        "short_explanation": row.get("explicacion_final"),
        "aspect_scores": None,  # Se enriquece desde ABSA en el service
        "context": {
            "weather_score": safe_float(row.get("score_clima")),
            "crowd_score": safe_float(row.get("score_aforo")),
            "weather_category": row.get("clima_categoria"),
            "crowd_level": row.get("nivel_aforo"),
        },
        "tourism_summary": None,
    }


def _enrich_with_catalog(item: dict[str, Any]) -> None:
    """
    Enriquece un item de recomendación con datos del catálogo turístico.
    Solo agrega campos complementarios, NO modifica scores.
    """
    dest_id = item.get("destination_id")
    if not dest_id:
        return

    enrichment = tourism_repository.get_enrichment_data(dest_id)
    if not enrichment:
        return

    item["city"] = enrichment.get("city")
    item["region"] = enrichment.get("region")
    item["category"] = enrichment.get("category")
    item["cover_image_url"] = enrichment.get("cover_image_url")
    item["tourism_summary"] = {
        "description": enrichment.get("description"),
        "experience_type": enrichment.get("experience_type"),
        "cover_image_url": enrichment.get("cover_image_url"),
    }
