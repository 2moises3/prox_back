"""
PROXVEL Backend - Tourism Repository.
Acceso a datos del catálogo turístico oficial desde destinations_catalog.csv.

Este repositorio maneja información complementaria de fuentes oficiales
(MINCETUR) que enriquece la presentación de destinos sin modificar
los scores de recomendación del núcleo de tesis.

Columnas del CSV:
  destination_id, destination, official_name, department, province,
  district, city, region, category, type, subtype, hierarchy,
  altitude_m, description, experience_type, visitor_info_summary,
  activities_summary, accessibility_summary, latitude, longitude,
  geofence_radius_m, cover_image_url, gallery_image_1..4,
  image_source, image_license_note, official_source_name,
  official_source_code, official_source_url, secondary_source_name,
  secondary_source_code, secondary_source_url, map_source, data_status

# TODO: Migrar a PostgreSQL en fase futura.
"""

import logging
from typing import Any

from app.repositories.csv_loader import get_data
from app.utils.normalizers import safe_float, safe_int

logger = logging.getLogger(__name__)

# Columnas de galería que se transforman en lista
GALLERY_COLUMNS = [
    "gallery_image_1",
    "gallery_image_2",
    "gallery_image_3",
    "gallery_image_4",
]


def _is_valid_value(value: Any) -> bool:
    """Verifica si un valor no es PENDIENTE, None, ni vacío."""
    if value is None:
        return False
    if isinstance(value, str):
        stripped = value.strip().upper()
        return stripped not in ("PENDIENTE", "", "NAN", "NONE", "NULL")
    return True


def _build_gallery_images(row: dict[str, Any]) -> list[str]:
    """
    Extrae gallery_image_1..4 y devuelve solo las que sean URLs válidas.
    No incluye imágenes marcadas como PENDIENTE.
    """
    images = []
    for col in GALLERY_COLUMNS:
        val = row.get(col)
        if _is_valid_value(val) and isinstance(val, str):
            images.append(val)
    return images


def _build_catalog_item(row: dict[str, Any]) -> dict[str, Any]:
    """Transforma una fila del catálogo CSV al formato de respuesta."""
    return {
        "destination_id": row.get("destination_id"),
        "destination": row.get("destination"),
        "official_name": row.get("official_name"),
        "department": row.get("department"),
        "province": row.get("province"),
        "district": row.get("district"),
        "city": row.get("city"),
        "region": row.get("region"),
        "category": row.get("category"),
        "type": row.get("type"),
        "subtype": row.get("subtype"),
        "hierarchy": safe_int(row.get("hierarchy")),
        "altitude_m": safe_int(row.get("altitude_m")),
        "description": row.get("description"),
        "experience_type": row.get("experience_type"),
        "visitor_info_summary": row.get("visitor_info_summary"),
        "activities_summary": row.get("activities_summary"),
        "accessibility_summary": row.get("accessibility_summary"),
        "latitude": safe_float(row.get("latitude")) if _is_valid_value(row.get("latitude")) else None,
        "longitude": safe_float(row.get("longitude")) if _is_valid_value(row.get("longitude")) else None,
        "geofence_radius_m": safe_float(row.get("geofence_radius_m")) if _is_valid_value(row.get("geofence_radius_m")) else None,
        "cover_image_url": row.get("cover_image_url") if _is_valid_value(row.get("cover_image_url")) else None,
        "gallery_images": _build_gallery_images(row),
        "image_source": row.get("image_source"),
        "image_license_note": row.get("image_license_note"),
        "official_source_name": row.get("official_source_name"),
        "official_source_code": str(row.get("official_source_code")) if row.get("official_source_code") else None,
        "official_source_url": row.get("official_source_url"),
        "secondary_source_name": row.get("secondary_source_name"),
        "secondary_source_code": str(safe_int(row.get("secondary_source_code"))) if _is_valid_value(row.get("secondary_source_code")) else None,
        "secondary_source_url": row.get("secondary_source_url"),
        "map_source": row.get("map_source") if _is_valid_value(row.get("map_source")) else None,
        "data_status": row.get("data_status"),
    }


def get_all_catalog() -> list[dict[str, Any]]:
    """Devuelve todos los destinos del catálogo turístico."""
    catalog_data = get_data("catalog")
    if catalog_data is None:
        logger.warning("Datos del catálogo turístico no disponibles")
        return []

    return [_build_catalog_item(row) for row in catalog_data]


def get_catalog_by_id(destination_id: str) -> dict[str, Any] | None:
    """Devuelve el detalle turístico de un destino por su ID."""
    catalog_data = get_data("catalog")
    if catalog_data is None:
        return None

    for row in catalog_data:
        if row.get("destination_id") == destination_id:
            return _build_catalog_item(row)

    return None


def get_map_markers() -> list[dict[str, Any]]:
    """
    Devuelve solo destinos con coordenadas válidas (no PENDIENTE).
    Cada marcador contiene la info mínima para un mapa.
    """
    catalog_data = get_data("catalog")
    if catalog_data is None:
        return []

    markers = []
    for row in catalog_data:
        lat = row.get("latitude")
        lon = row.get("longitude")

        if not _is_valid_value(lat) or not _is_valid_value(lon):
            continue

        lat_float = safe_float(lat)
        lon_float = safe_float(lon)

        if lat_float is None or lon_float is None:
            continue

        markers.append({
            "destination_id": row.get("destination_id"),
            "destination": row.get("destination"),
            "latitude": lat_float,
            "longitude": lon_float,
            "category": row.get("category"),
            "label": row.get("destination"),
        })

    return markers


def get_enrichment_data(destination_id: str) -> dict[str, Any] | None:
    """
    Devuelve datos del catálogo para enriquecer otros endpoints.
    Solo campos relevantes para enriquecimiento (no el detalle completo).
    """
    catalog_data = get_data("catalog")
    if catalog_data is None:
        return None

    for row in catalog_data:
        if row.get("destination_id") == destination_id:
            return {
                "city": row.get("city"),
                "region": row.get("region"),
                "category": row.get("category"),
                "type": row.get("type"),
                "subtype": row.get("subtype"),
                "cover_image_url": row.get("cover_image_url") if _is_valid_value(row.get("cover_image_url")) else None,
                "official_source_name": row.get("official_source_name"),
                "description": row.get("description"),
                "experience_type": row.get("experience_type"),
                "official_name": row.get("official_name"),
                "official_source_url": row.get("official_source_url"),
                "gallery_images": _build_gallery_images(row),
                "data_status": row.get("data_status"),
            }

    return None
