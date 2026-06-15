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

_MONTH_NAMES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def get_all_destinations(city: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    try:
        db = SessionLocal()
        try:
            if db.query(Destination).count() == 0:
                logger.info("PostgreSQL: Tabla destinations vacía. Fallback a CSV.")
                return fallback_repo.get_all_destinations(city=city, limit=limit)
            
            logger.info("PostgreSQL: Leyendo destinations.")
            dests_db = db.scalars(select(Destination)).all()
            
            from app.services import destination_media_service
            active_covers = destination_media_service.get_covers_batch(db)

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
                    "cover_image_url": active_covers.get(dest.destination_id),
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


def get_destination_by_id(destination_id: str, month: int | None = None) -> dict[str, Any] | None:
    try:
        db = SessionLocal()
        try:
            if db.query(Destination).count() == 0:
                logger.info("PostgreSQL: Tabla destinations vacía. Fallback a CSV.")
                return fallback_repo.get_destination_by_id(destination_id, month=month)

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

            # Climate: por mes solicitado o el último disponible
            clima_q = select(ClimateScore).where(ClimateScore.destination_id == destination_id)
            if month is not None:
                clima_q = clima_q.where(ClimateScore.month == month)
            clima = db.scalar(clima_q.order_by(ClimateScore.id.desc()))
            weather_detail = {}
            if clima:
                weather_detail = {
                    "month": clima.month,
                    "month_name": _MONTH_NAMES.get(clima.month),
                    "temp_prom": clima.temp_prom,
                    "pp": clima.pp,
                    "clima_categoria": clima.clima_categoria,
                    "score_clima": clima.score_clima,
                }

            # Crowd: por mes solicitado (último año con ese mes) o el último disponible
            aforo_q = select(CrowdScore).where(CrowdScore.destination_id == destination_id)
            if month is not None:
                aforo_q = aforo_q.where(CrowdScore.month == month)
            aforo = db.scalar(aforo_q.order_by(CrowdScore.year.desc(), CrowdScore.id.desc()))
            crowd_detail = {}
            if aforo:
                crowd_detail = {
                    "month": aforo.month,
                    "month_name": _MONTH_NAMES.get(aforo.month),
                    "periodo": aforo.periodo,
                    "visitantes_mes": aforo.visitantes_mes,
                    "aforo_normalizado": aforo.aforo_normalizado,
                    "nivel_aforo": aforo.nivel_aforo,
                    "score_aforo_base": aforo.score_aforo_base,
                }

            from app.services import destination_media_service
            media = destination_media_service.get_destination_media(db, destination_id)
            cover_url = media.cover.url if media.cover else None

            enrichment = db_tourism_repository.get_enrichment_data(destination_id, db=db)
            tourism_info = None
            if enrichment:
                tourism_info = {
                    "official_name": enrichment.get("official_name"),
                    "description": enrichment.get("description"),
                    "experience_type": enrichment.get("experience_type"),
                    "gallery_images": [g.url for g in media.gallery] if media.gallery else [],
                    "official_source_name": enrichment.get("official_source_name"),
                    "official_source_url": enrichment.get("official_source_url"),
                }

            return {
                "destination_id": dest.destination_id,
                "destination": dest.destination,
                "city": enrichment.get("city") if enrichment else None,
                "region": enrichment.get("region") if enrichment else None,
                "category": enrichment.get("category") if enrichment else None,
                "type": enrichment.get("type") if enrichment else None,
                "subtype": enrichment.get("subtype") if enrichment else None,
                "cover_image_url": cover_url,
                "official_source_name": enrichment.get("official_source_name") if enrichment else None,
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
