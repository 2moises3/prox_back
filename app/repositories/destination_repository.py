"""
PROXVEL Backend - Destination Repository.
Acceso a datos de destinos consolidados desde múltiples CSV.

Fuentes de datos:
  - matriz_absa_normalizada.csv → nombre + scores ABSA
  - clima_scores.csv → contexto climático por mes
  - aforo_scores.csv → contexto de aforo/concurrencia
  - destinations_catalog.csv → catálogo turístico complementario (Fase 1B)

El catálogo complementario enriquece city, region, category, etc.
sin modificar los scores ABSA ni el ranking de tesis.

# TODO: Migrar a PostgreSQL en fase futura.
"""

import logging
from typing import Any

from app.repositories.csv_loader import get_data
from app.repositories import tourism_repository
from app.utils.normalizers import generate_destination_id, safe_float

logger = logging.getLogger(__name__)

# ── Aspectos ABSA conocidos ────────────────────────────────────────
ASPECT_COLUMNS = [
    "accesibilidad",
    "aforo_multitudes",
    "alojamiento",
    "atencion_servicio",
    "atractivos",
    "clima",
    "costos",
    "gastronomia",
    "limpieza",
    "seguridad",
]


def get_all_destinations(
    city: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Devuelve lista de destinos detectados en los CSV ABSA,
    enriquecidos con datos del catálogo turístico.
    """
    absa_data = get_data("absa")
    if absa_data is None:
        logger.warning("Datos ABSA no disponibles")
        return []

    destinations = []
    for row in absa_data:
        name = row.get("destination")
        if not name:
            continue

        dest_id = generate_destination_id(name)

        # Datos base desde ABSA
        dest = {
            "destination_id": dest_id,
            "destination": name,
            "city": None,
            "category": None,
            "region": None,
            "type": None,
            "subtype": None,
            "cover_image_url": None,
            "official_source_name": None,
        }

        # Enriquecer desde catálogo turístico (Fase 1B)
        enrichment = tourism_repository.get_enrichment_data(dest_id)
        if enrichment:
            dest["city"] = enrichment.get("city")
            dest["region"] = enrichment.get("region")
            dest["category"] = enrichment.get("category")
            dest["type"] = enrichment.get("type")
            dest["subtype"] = enrichment.get("subtype")
            dest["cover_image_url"] = enrichment.get("cover_image_url")
            dest["official_source_name"] = enrichment.get("official_source_name")

        destinations.append(dest)

    # Filtro por ciudad (ahora funcional con datos del catálogo)
    if city:
        destinations = [
            d for d in destinations
            if d.get("city") and city.lower() in d["city"].lower()
        ]

    return destinations[:limit]


def get_destination_by_id(destination_id: str) -> dict[str, Any] | None:
    """
    Devuelve el detalle completo de un destino, incluyendo:
    - scores ABSA por aspecto
    - contexto climático (último/promedio disponible)
    - contexto de aforo (último disponible)
    - tourism_info desde catálogo turístico (Fase 1B)
    """
    absa_data = get_data("absa")
    if absa_data is None:
        return None

    # Buscar destino en datos ABSA
    target_row = None
    for row in absa_data:
        name = row.get("destination", "")
        if generate_destination_id(name) == destination_id:
            target_row = row
            break

    if target_row is None:
        return None

    dest_name = target_row["destination"]

    # Construir scores ABSA
    aspect_scores = {}
    for col in ASPECT_COLUMNS:
        aspect_scores[col] = safe_float(target_row.get(col))

    # Obtener contexto climático
    weather_context = _get_weather_context(dest_name)

    # Obtener contexto de aforo
    crowd_context = _get_crowd_context(dest_name)

    # Obtener enriquecimiento del catálogo (Fase 1B)
    enrichment = tourism_repository.get_enrichment_data(destination_id)

    # Construir tourism_info
    tourism_info = None
    if enrichment:
        tourism_info = {
            "official_name": enrichment.get("official_name"),
            "description": enrichment.get("description"),
            "experience_type": enrichment.get("experience_type"),
            "gallery_images": enrichment.get("gallery_images", []),
            "official_source_name": enrichment.get("official_source_name"),
            "official_source_url": enrichment.get("official_source_url"),
        }

    return {
        "destination_id": generate_destination_id(dest_name),
        "destination": dest_name,
        "city": enrichment.get("city") if enrichment else None,
        "region": enrichment.get("region") if enrichment else None,
        "category": enrichment.get("category") if enrichment else None,
        "aspect_scores": aspect_scores,
        "context": {
            "weather_score": weather_context.get("score_clima"),
            "crowd_score": crowd_context.get("score_aforo_base"),
            "weather_category": weather_context.get("clima_categoria"),
            "crowd_level": crowd_context.get("nivel_aforo"),
        },
        "weather_detail": weather_context,
        "crowd_detail": crowd_context,
        "tourism_info": tourism_info,
    }


def _get_weather_context(destination_name: str) -> dict[str, Any]:
    """Obtiene el contexto climático más reciente para un destino."""
    clima_data = get_data("clima")
    if clima_data is None:
        return {}

    # Filtrar por destino y tomar el último registro disponible
    dest_rows = [
        r for r in clima_data
        if r.get("destination") == destination_name
    ]

    if not dest_rows:
        return {}

    # Tomar el último mes disponible
    last = dest_rows[-1]
    return {
        "month_name": last.get("month_name"),
        "temp_prom": safe_float(last.get("temp_prom")),
        "pp": safe_float(last.get("pp")),
        "clima_categoria": last.get("clima_categoria"),
        "score_clima": safe_float(last.get("score_clima")),
    }


def _get_crowd_context(destination_name: str) -> dict[str, Any]:
    """Obtiene el contexto de aforo más reciente para un destino."""
    aforo_data = get_data("aforo")
    if aforo_data is None:
        return {}

    # Filtrar por destino
    dest_rows = [
        r for r in aforo_data
        if r.get("destination") == destination_name
    ]

    if not dest_rows:
        return {}

    # Tomar el último período disponible
    last = dest_rows[-1]
    return {
        "periodo": last.get("periodo"),
        "visitantes_mes": safe_float(last.get("visitantes_mes")),
        "aforo_normalizado": safe_float(last.get("aforo_normalizado")),
        "nivel_aforo": last.get("nivel_aforo"),
        "score_aforo_base": safe_float(last.get("score_aforo_base")),
    }
