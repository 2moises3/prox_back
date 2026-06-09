"""
PROXVEL Backend - DB Destination Repository.
Acceso a datos de destinos desde PostgreSQL con fallback a CSV.
"""

import logging
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config.database import SessionLocal
from app.repositories import destination_repository as fallback_repo
from app.repositories import db_tourism_repository
from app.models.destination_model import Destination
from app.models.aspect_score_model import DestinationAspectScore
from app.models.climate_score_model import ClimateScore
from app.models.crowd_score_model import CrowdScore

logger = logging.getLogger(__name__)


def get_all_destinations(city: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    try:
        db = SessionLocal()
        try:
            if db.query(Destination).count() == 0:
                logger.info("PostgreSQL: Tabla destinations vacía. Fallback a CSV.")
                return fallback_repo.get_all_destinations(city=city, limit=limit)
            
            logger.info("PostgreSQL: Leyendo destinations.")
            dests_db = db.scalars(select(Destination)).all()
            destinations = []
            
            for dest in dests_db:
                item = {
                    "destination_id": dest.destination_id,
                    "destination": dest.destination,
                    "city": None,
                    "category": None,
                    "region": None,
                    "type": None,
                    "subtype": None,
                    "cover_image_url": None,
                    "official_source_name": None,
                }
                enrichment = db_tourism_repository.get_enrichment_data(dest.destination_id, db=db)
                if enrichment:
                    item.update({
                        "city": enrichment.get("city"),
                        "category": enrichment.get("category"),
                        "region": enrichment.get("region"),
                        "type": enrichment.get("type"),
                        "subtype": enrichment.get("subtype"),
                        "cover_image_url": enrichment.get("cover_image_url"),
                        "official_source_name": enrichment.get("official_source_name"),
                    })
                destinations.append(item)
            
            if city:
                destinations = [d for d in destinations if d.get("city") and city.lower() in d["city"].lower()]
            
            return destinations[:limit]
        finally:
            db.close()
    except Exception as e:
        logger.error("PostgreSQL fallback activado en get_all_destinations: %s", e)
        return fallback_repo.get_all_destinations(city=city, limit=limit)


def get_destination_by_id(destination_id: str) -> dict[str, Any] | None:
    try:
        db = SessionLocal()
        try:
            if db.query(Destination).count() == 0:
                logger.info("PostgreSQL: Tabla destinations vacía. Fallback a CSV.")
                return fallback_repo.get_destination_by_id(destination_id)

            logger.info(f"PostgreSQL: Leyendo detalle para destination_id={destination_id}.")
            dest = db.scalar(select(Destination).where(Destination.destination_id == destination_id))
            if not dest:
                return None

            scores = db.scalar(select(DestinationAspectScore).where(DestinationAspectScore.destination_id == destination_id))
            aspect_scores = {}
            if scores:
                aspect_scores = {
                    "accesibilidad": scores.accesibilidad,
                    "aforo_multitudes": scores.aforo_multitudes,
                    "alojamiento": scores.alojamiento,
                    "atencion_servicio": scores.atencion_servicio,
                    "atractivos": scores.atractivos,
                    "clima": scores.clima,
                    "costos": scores.costos,
                    "gastronomia": scores.gastronomia,
                    "limpieza": scores.limpieza,
                    "seguridad": scores.seguridad,
                }
            else:
                # Initialize with Nones matching JSON contract
                aspect_scores = {k: None for k in ["accesibilidad", "aforo_multitudes", "alojamiento", "atencion_servicio", "atractivos", "clima", "costos", "gastronomia", "limpieza", "seguridad"]}

            # Get latest climate
            clima = db.scalar(select(ClimateScore).where(ClimateScore.destination_id == destination_id).order_by(ClimateScore.id.desc()))
            weather_detail = {}
            if clima:
                # The model does not store month_name right now, but for contract consistency we can try to derive or just leave None
                weather_detail = {
                    "month_name": None,  # Mapeable en el futuro si se añade al modelo
                    "temp_prom": clima.temp_prom,
                    "pp": clima.pp,
                    "clima_categoria": clima.clima_categoria,
                    "score_clima": clima.score_clima,
                }

            # Get latest crowd
            aforo = db.scalar(select(CrowdScore).where(CrowdScore.destination_id == destination_id).order_by(CrowdScore.id.desc()))
            crowd_detail = {}
            if aforo:
                crowd_detail = {
                    "periodo": aforo.periodo,
                    "visitantes_mes": aforo.visitantes_mes,
                    "aforo_normalizado": aforo.aforo_normalizado,
                    "nivel_aforo": aforo.nivel_aforo,
                    "score_aforo_base": aforo.score_aforo_base,
                }

            enrichment = db_tourism_repository.get_enrichment_data(destination_id, db=db)
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
                "destination_id": dest.destination_id,
                "destination": dest.destination,
                "city": enrichment.get("city") if enrichment else None,
                "region": enrichment.get("region") if enrichment else None,
                "category": enrichment.get("category") if enrichment else None,
                "aspect_scores": aspect_scores,
                "context": {
                    "weather_score": weather_detail.get("score_clima"),
                    "crowd_score": crowd_detail.get("score_aforo_base"),
                    "weather_category": weather_detail.get("clima_categoria"),
                    "crowd_level": crowd_detail.get("nivel_aforo"),
                },
                "weather_detail": weather_detail,
                "crowd_detail": crowd_detail,
                "tourism_info": tourism_info,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error("PostgreSQL fallback activado en get_destination_by_id: %s", e)
        return fallback_repo.get_destination_by_id(destination_id)
