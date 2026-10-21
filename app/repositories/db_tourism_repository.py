"""
PROXVEL Backend - DB Tourism Repository.
Acceso a datos del catálogo turístico oficial desde PostgreSQL (fuente única).
"""

import logging
from typing import Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from app.config.database import SessionLocal
from app.models.tourism_catalog_model import TourismCatalog
from app.models.destination_tag_model import DestinationTag

logger = logging.getLogger(__name__)


def _build_catalog_item(catalog: TourismCatalog, db: Session) -> dict[str, Any]:
    """Transforma el ORM al dict esperado por el contrato JSON (imágenes desde destination_media)."""
    from app.services import destination_media_service

    media = destination_media_service.get_destination_media(db, catalog.destination_id)
    tags = db.scalars(
        select(DestinationTag.tag).where(DestinationTag.destination_id == catalog.destination_id)
    ).all()
    return {
        "destination_id": catalog.destination_id,
        "destination": catalog.destination.destination if catalog.destination else None,
        "region": catalog.region,
        "city": catalog.city,
        "category": catalog.category,
        "altitude_m": catalog.altitude_m,
        "description": catalog.description,
        "activities_summary": catalog.activities_summary,
        "visitor_info_summary": catalog.visitor_info_summary,
        "accessibility_summary": catalog.accessibility_summary,
        "recommended_duration": catalog.recommended_duration,
        "how_to_get": catalog.how_to_get,
        "difficulty": catalog.difficulty,
        "official_website": catalog.official_website,
        "cost_level": catalog.cost_level,
        "latitude": catalog.latitude,
        "longitude": catalog.longitude,
        "cover_image_url": media.cover.url if media.cover else None,
        "gallery_images": [g.url for g in media.gallery] if media.gallery else [],
        "data_status": catalog.data_status,
        "interest_tags": sorted(t for t in tags if t),
    }


def get_all_catalog() -> list[dict[str, Any]]:
    try:
        db = SessionLocal()
        try:
            total = db.query(TourismCatalog).count()
            if total == 0:
                logger.info("PostgreSQL: Tabla tourism_catalog vacía.")
                return []

            logger.info("PostgreSQL: Leyendo tourism_catalog.")
            catalogs = db.scalars(select(TourismCatalog).options(joinedload(TourismCatalog.destination))).all()
            return [_build_catalog_item(c, db) for c in catalogs]
        finally:
            db.close()
    except Exception as e:
        logger.error("Error en get_all_catalog: %s", e)
        return []


def get_catalog_by_id(destination_id: str) -> dict[str, Any] | None:
    try:
        db = SessionLocal()
        try:
            if db.query(TourismCatalog).count() == 0:
                logger.info("PostgreSQL: Tabla tourism_catalog vacía.")
                return None

            logger.info(f"PostgreSQL: Leyendo catalog para {destination_id}.")
            catalog = db.scalar(
                select(TourismCatalog)
                .options(joinedload(TourismCatalog.destination))
                .where(TourismCatalog.destination_id == destination_id)
            )
            return _build_catalog_item(catalog, db) if catalog else None
        finally:
            db.close()
    except Exception as e:
        logger.error("Error en get_catalog_by_id: %s", e)
        return None


def get_map_markers() -> list[dict[str, Any]]:
    try:
        db = SessionLocal()
        try:
            if db.query(TourismCatalog).count() == 0:
                logger.info("PostgreSQL: Tabla tourism_catalog vacía.")
                return []

            logger.info("PostgreSQL: Leyendo map_markers.")
            catalogs = db.scalars(
                select(TourismCatalog)
                .options(joinedload(TourismCatalog.destination))
                .where(TourismCatalog.latitude.is_not(None))
                .where(TourismCatalog.longitude.is_not(None))
            ).all()

            markers = []
            for c in catalogs:
                # Ocultar del mapa público los destinos inactivos.
                if c.destination and not c.destination.is_active:
                    continue
                dest_name = c.destination.destination if c.destination else c.destination_id
                markers.append({
                    "destination_id": c.destination_id,
                    "destination": dest_name,
                    "latitude": c.latitude,
                    "longitude": c.longitude,
                    "category": c.category,
                    "label": dest_name,
                })
            return markers
        finally:
            db.close()
    except Exception as e:
        logger.error("Error en get_map_markers: %s", e)
        return []


def get_enrichment_data(destination_id: str, db: Session | None = None) -> dict[str, Any] | None:
    """Puede recibir una sesión para evitar crear múltiples sesiones cuando se llama en loop."""
    try:
        session = db or SessionLocal()
        try:
            catalog = session.scalar(
                select(TourismCatalog).where(TourismCatalog.destination_id == destination_id)
            )
            if not catalog:
                return None

            return {
                "region": catalog.region,
                "city": catalog.city,
                "category": catalog.category,
                "altitude_m": catalog.altitude_m,
                "description": catalog.description,
                "activities_summary": catalog.activities_summary,
                "visitor_info_summary": catalog.visitor_info_summary,
                "accessibility_summary": catalog.accessibility_summary,
                "recommended_duration": catalog.recommended_duration,
                "how_to_get": catalog.how_to_get,
                "difficulty": catalog.difficulty,
                "official_website": catalog.official_website,
                "cost_level": catalog.cost_level,
                "latitude": catalog.latitude,
                "longitude": catalog.longitude,
                "data_status": catalog.data_status,
            }
        finally:
            if not db:
                session.close()
    except Exception as e:
        logger.error("Error en get_enrichment_data: %s", e)
        return None
