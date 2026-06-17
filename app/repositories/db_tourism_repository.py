"""
PROXVEL Backend - DB Tourism Repository.
Acceso a datos del catálogo turístico oficial desde PostgreSQL con fallback a CSV.
"""

import logging
from typing import Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from app.config.database import SessionLocal
from app.repositories import tourism_repository as fallback_repo
from app.models.tourism_catalog_model import TourismCatalog

logger = logging.getLogger(__name__)


def _build_catalog_item(catalog: TourismCatalog) -> dict[str, Any]:
    """Transforma el ORM al dict esperado por el contrato JSON."""
    images = []
    for img in [catalog.gallery_image_1, catalog.gallery_image_2, catalog.gallery_image_3, catalog.gallery_image_4]:
        if img:
            images.append(img)
            
    return {
        "destination_id": catalog.destination_id,
        "destination": catalog.destination.destination if catalog.destination else None,
        "official_name": catalog.official_name,
        "department": catalog.department,
        "province": catalog.province,
        "district": catalog.district,
        "city": catalog.city,
        "region": catalog.region,
        "category": catalog.category,
        "type": catalog.type_,
        "subtype": catalog.subtype,
        "hierarchy": catalog.hierarchy,
        "altitude_m": catalog.altitude_m,
        "description": catalog.description,
        "experience_type": catalog.experience_type,
        "visitor_info_summary": catalog.visitor_info_summary,
        "activities_summary": catalog.activities_summary,
        "accessibility_summary": catalog.accessibility_summary,
        "latitude": catalog.latitude,
        "longitude": catalog.longitude,
        "geofence_radius_m": catalog.geofence_radius_m,
        "cover_image_url": catalog.cover_image_url,
        "gallery_images": images,
        "image_source": catalog.image_source,
        "image_license_note": catalog.image_license_note,
        "official_source_name": catalog.official_source_name,
        "official_source_code": catalog.official_source_code,
        "official_source_url": catalog.official_source_url,
        "secondary_source_name": catalog.secondary_source_name,
        "secondary_source_code": catalog.secondary_source_code,
        "secondary_source_url": catalog.secondary_source_url,
        "map_source": catalog.map_source,
        "data_status": catalog.data_status,
    }


def get_all_catalog() -> list[dict[str, Any]]:
    try:
        db = SessionLocal()
        try:
            total = db.query(TourismCatalog).count()
            if total == 0:
                logger.info("PostgreSQL: Tabla tourism_catalog vacía. Fallback a CSV.")
                return fallback_repo.get_all_catalog()

            logger.info("PostgreSQL: Leyendo tourism_catalog.")
            catalogs = db.scalars(select(TourismCatalog).options(joinedload(TourismCatalog.destination))).all()
            return [_build_catalog_item(c) for c in catalogs]
        finally:
            db.close()
    except Exception as e:
        logger.error("PostgreSQL fallback activado en get_all_catalog: %s", e)
        return fallback_repo.get_all_catalog()


def get_catalog_by_id(destination_id: str) -> dict[str, Any] | None:
    try:
        db = SessionLocal()
        try:
            if db.query(TourismCatalog).count() == 0:
                logger.info("PostgreSQL: Tabla tourism_catalog vacía. Fallback a CSV.")
                return fallback_repo.get_catalog_by_id(destination_id)

            logger.info(f"PostgreSQL: Leyendo catalog para {destination_id}.")
            catalog = db.scalar(
                select(TourismCatalog)
                .options(joinedload(TourismCatalog.destination))
                .where(TourismCatalog.destination_id == destination_id)
            )
            return _build_catalog_item(catalog) if catalog else None
        finally:
            db.close()
    except Exception as e:
        logger.error("PostgreSQL fallback activado en get_catalog_by_id: %s", e)
        return fallback_repo.get_catalog_by_id(destination_id)


def get_map_markers() -> list[dict[str, Any]]:
    try:
        db = SessionLocal()
        try:
            if db.query(TourismCatalog).count() == 0:
                logger.info("PostgreSQL: Tabla tourism_catalog vacía. Fallback a CSV.")
                return fallback_repo.get_map_markers()

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
        logger.error("PostgreSQL fallback activado en get_map_markers: %s", e)
        return fallback_repo.get_map_markers()


def get_enrichment_data(destination_id: str, db: Session | None = None) -> dict[str, Any] | None:
    """Puede recibir una sesión para evitar crear múltiples sesiones cuando se llama en loop."""
    try:
        session = db or SessionLocal()
        try:
            if session.query(TourismCatalog).count() == 0:
                return fallback_repo.get_enrichment_data(destination_id)

            catalog = session.scalar(
                select(TourismCatalog).where(TourismCatalog.destination_id == destination_id)
            )
            if not catalog:
                return None

            images = []
            for img in [catalog.gallery_image_1, catalog.gallery_image_2, catalog.gallery_image_3, catalog.gallery_image_4]:
                if img:
                    images.append(img)

            return {
                "city": catalog.city,
                "region": catalog.region,
                "category": catalog.category,
                "type": catalog.type_,
                "subtype": catalog.subtype,
                "cover_image_url": catalog.cover_image_url,
                "official_source_name": catalog.official_source_name,
                "description": catalog.description,
                "experience_type": catalog.experience_type,
                "official_name": catalog.official_name,
                "official_source_url": catalog.official_source_url,
                "gallery_images": images,
            }
        finally:
            if not db:
                session.close()
    except Exception as e:
        logger.error("PostgreSQL fallback activado en get_enrichment_data: %s", e)
        return fallback_repo.get_enrichment_data(destination_id)
