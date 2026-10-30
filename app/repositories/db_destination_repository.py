"""
PROXVEL Backend - DB Destination Repository.
Acceso a datos de destinos desde PostgreSQL (fuente única).
"""

import logging
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config.database import SessionLocal
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


def get_all_destinations(city: str | None = None, limit: int = 50, include_inactive: bool = False) -> list[dict[str, Any]]:
    try:
        db = SessionLocal()
        try:
            if db.query(Destination).count() == 0:
                logger.info("PostgreSQL: Tabla destinations vacía.")
                return []

            logger.info("PostgreSQL: Leyendo destinations.")
            stmt = select(Destination)
            if not include_inactive:
                # Catálogo público: ocultar destinos inactivos.
                stmt = stmt.where(Destination.is_active.is_(True))
            dests_db = db.scalars(stmt).all()

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
                    "cover_image_url": active_covers.get(dest.destination_id),
                    "is_active": dest.is_active,
                    "in_engine": dest.in_engine,
                    "cost_level": None,
                    "data_status": None,
                    "latitude": None,
                    "longitude": None,
                }
                enrichment = db_tourism_repository.get_enrichment_data(dest.destination_id, db=db)
                if enrichment:
                    item.update({
                        "city": enrichment.get("city"),
                        "category": enrichment.get("category"),
                        "region": enrichment.get("region"),
                        "data_status": enrichment.get("data_status"),
                        "cost_level": enrichment.get("cost_level"),
                        "latitude": enrichment.get("latitude"),
                        "longitude": enrichment.get("longitude"),
                    })
                destinations.append(item)
            
            if city:
                destinations = [d for d in destinations if d.get("city") and city.lower() in d["city"].lower()]
            
            return destinations[:limit]
        finally:
            db.close()
    except Exception as e:
        logger.error("Error en get_all_destinations: %s", e)
        return []


def get_destination_by_id(destination_id: str, month: int | None = None, include_inactive: bool = False) -> dict[str, Any] | None:
    # Sin mes explícito se usa el actual: así el clima y aforo del detalle nunca quedan vacíos.
    if month is None:
        from datetime import datetime, timezone
        month = datetime.now(timezone.utc).month
    try:
        db = SessionLocal()
        try:
            if db.query(Destination).count() == 0:
                logger.info("PostgreSQL: Tabla destinations vacía.")
                return None

            logger.info(f"PostgreSQL: Leyendo detalle para destination_id={destination_id}.")
            dest = db.scalar(select(Destination).where(Destination.destination_id == destination_id))
            if not dest:
                return None
                
            if not include_inactive and not dest.is_active:
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

            # Fallback: ClimateScore/CrowdScore son parciales (pocos destinos).
            # Si falta clima/aforo del mes, se usa destination_month_context, que
            # es la fuente COMPLETA del motor (clima/aforo de los 10 destinos).
            if (not weather_detail or not crowd_detail) and month is not None:
                from app.models.destination_month_context_model import DestinationMonthContext
                ctx = db.scalar(
                    select(DestinationMonthContext).where(
                        DestinationMonthContext.destination_id == destination_id,
                        DestinationMonthContext.month == month,
                    )
                )
                if ctx:
                    if not weather_detail and ctx.clima_score is not None:
                        weather_detail = {
                            "month": ctx.month,
                            "month_name": _MONTH_NAMES.get(ctx.month),
                            "temp_prom": ctx.temp_prom,
                            "pp": ctx.pp,
                            "clima_categoria": ctx.clima_nivel,
                            "score_clima": ctx.clima_score,
                        }
                    if not crowd_detail and ctx.aforo_score is not None:
                        crowd_detail = {
                            "month": ctx.month,
                            "month_name": _MONTH_NAMES.get(ctx.month),
                            "periodo": None,
                            "visitantes_mes": ctx.visitantes_medios,
                            "aforo_normalizado": None,
                            "nivel_aforo": ctx.aforo_nivel,
                            "score_aforo_base": ctx.aforo_score,
                        }

            from app.services import destination_media_service
            media = destination_media_service.get_destination_media(db, destination_id)
            cover_url = media.cover.url if media.cover else None

            enrichment = db_tourism_repository.get_enrichment_data(destination_id, db=db)
            tourism_info = None
            if enrichment:
                tourism_info = {
                    "altitude_m": enrichment.get("altitude_m"),
                    "description": enrichment.get("description"),
                    "activities_summary": enrichment.get("activities_summary"),
                    "visitor_info_summary": enrichment.get("visitor_info_summary"),
                    "accessibility_summary": enrichment.get("accessibility_summary"),
                    "recommended_duration": enrichment.get("recommended_duration"),
                    "how_to_get": enrichment.get("how_to_get"),
                    "difficulty": enrichment.get("difficulty"),
                    "official_website": enrichment.get("official_website"),
                    "latitude": enrichment.get("latitude"),
                    "longitude": enrichment.get("longitude"),
                    "geofence_radius_meters": enrichment.get("geofence_radius_meters"),
                    "min_dwell_minutes": enrichment.get("min_dwell_minutes"),
                    "gallery_images": [g.url for g in media.gallery] if media.gallery else [],
                }

            return {
                "destination_id": dest.destination_id,
                "destination": dest.destination,
                "is_active": dest.is_active,
                "in_engine": dest.in_engine,
                "cost_level": enrichment.get("cost_level") if enrichment else None,
                "city": enrichment.get("city") if enrichment else None,
                "region": enrichment.get("region") if enrichment else None,
                "category": enrichment.get("category") if enrichment else None,
                "cover_image_url": cover_url,
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
                "data_status": enrichment.get("data_status") if enrichment else None,
            }
        finally:
            db.close()
    except Exception as e:
        logger.error("Error en get_destination_by_id: %s", e)
        return None

_ABSA_ASPECTS = [
    "accesibilidad", "aforo_multitudes", "alojamiento", "atencion_servicio",
    "atractivos", "clima", "costos", "gastronomia", "limpieza", "seguridad",
]


def upsert_aspect_scores(db: Session, destination_id: str, scores: dict[str, float | None]) -> None:
    """Inserta o actualiza los puntajes ABSA de un destino."""
    existing = db.scalar(
        select(DestinationAspectScore).where(DestinationAspectScore.destination_id == destination_id)
    )
    if existing:
        for key, val in scores.items():
            if hasattr(existing, key):
                setattr(existing, key, val)
    else:
        valid = {k: v for k, v in scores.items() if k in _ABSA_ASPECTS}
        db.add(DestinationAspectScore(destination_id=destination_id, **valid))
    db.commit()


def create_destination_admin(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    """Crea un destino nuevo con su entrada de catálogo turístico y puntajes ABSA neutros."""
    import re

    name: str = data["name"].strip()

    # Generar slug si no viene
    destination_id: str = data.get("destination_id") or ""
    if not destination_id:
        slug = name.lower()
        for src, dst in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n"),("ü","u")]:
            slug = slug.replace(src, dst)
        slug = re.sub(r"[^a-z0-9\s-]", "", slug)
        slug = re.sub(r"[\s-]+", "-", slug).strip("-")
        destination_id = slug

    # Unicidad
    existing = db.scalar(select(Destination).where(Destination.destination_id == destination_id))
    if existing:
        raise ValueError(f"Ya existe un destino con el ID '{destination_id}'")

    dest = Destination(destination_id=destination_id, destination=name)
    db.add(dest)
    db.flush()

    from app.models.tourism_catalog_model import TourismCatalog
    has_editorial = bool(
        data.get("city") and data.get("region") and
        data.get("category") and data.get("description")
    )
    catalog = TourismCatalog(
        destination_id=destination_id,
        city=data.get("city"),
        region=data.get("region"),
        category=data.get("category"),
        description=data.get("description"),
        data_status="ready" if has_editorial else "pending_info",
    )
    db.add(catalog)

    # Puntajes ABSA neutros (0.5) para que el destino entre al motor desde el primer momento.
    # El admin ajusta los reales vía importación CSV o edición manual.
    neutral = {a: 0.5 for a in _ABSA_ASPECTS}
    db.add(DestinationAspectScore(destination_id=destination_id, **neutral))

    db.commit()

    return {
        "destination_id": destination_id,
        "destination": name,
        "city": data.get("city"),
        "region": data.get("region"),
        "category": data.get("category"),
    }


def set_destination_status(db: Session, destination_id: str, is_active: bool) -> dict[str, Any] | None:
    """Activa o desactiva un destino (soft visibility). Devuelve el detalle actualizado."""
    dest = db.scalar(select(Destination).where(Destination.destination_id == destination_id))
    if not dest:
        return None
    dest.is_active = is_active
    db.commit()
    return get_destination_by_id(destination_id, include_inactive=True)


def update_destination_admin(db: Session, destination_id: str, update_data: dict[str, Any]) -> dict[str, Any] | None:
    try:
        from app.models.tourism_catalog_model import TourismCatalog
        
        dest = db.scalar(select(Destination).where(Destination.destination_id == destination_id))
        if not dest:
            return None
            
        tourism = db.scalar(select(TourismCatalog).where(TourismCatalog.destination_id == destination_id))
        if not tourism:
            # Create tourism catalog entry if it doesn't exist to allow updating
            tourism = TourismCatalog(destination_id=destination_id)
            db.add(tourism)
            
        # Update Destination table
        if "name" in update_data and update_data["name"] is not None:
            dest.destination = update_data["name"]

        # Campos editables de TourismCatalog.
        _CATALOG_FIELDS = [
            "city", "region", "category", "altitude_m", "description",
            "activities_summary", "visitor_info_summary", "accessibility_summary",
            "recommended_duration", "how_to_get", "official_website",
            "latitude", "longitude",
            "geofence_radius_meters", "min_dwell_minutes",
        ]
        for field in _CATALOG_FIELDS:
            if field in update_data and update_data[field] is not None:
                setattr(tourism, field, update_data[field])

        # Nivel de costo y dificultad: aceptan null para borrarse (el resto de campos ignora null).
        if "cost_level" in update_data:
            tourism.cost_level = update_data["cost_level"] or None
        if "difficulty" in update_data:
            tourism.difficulty = update_data["difficulty"] or None

        db.commit()

        # Recalcular data_status tras cambios editoriales
        from app.services.destination_metric_sync_service import recalculate_status
        recalculate_status(db, destination_id)
        db.commit()
        
        # Return updated detail
        return get_destination_by_id(destination_id, include_inactive=True)
        
    except Exception as e:
        db.rollback()
        logger.error("Error updating destination %s: %s", destination_id, e)
        raise e


def delete_destination_admin(db: Session, destination_id: str) -> bool:
    """Elimina definitivamente un destino y todos sus datos en cascada manual."""
    try:
        from app.models.tourism_catalog_model import TourismCatalog
        from app.models.aspect_score_model import DestinationAspectScore
        from app.models.climate_score_model import ClimateScore
        from app.models.crowd_score_model import CrowdScore
        from app.models.contextual_ranking_model import ContextualRanking
        from app.models.favorite_model import Favorite
        from app.models.review_model import Review
        from app.models.visit_model import Visit
        from app.models.destination_media_model import DestinationMedia

        dest = db.scalar(select(Destination).where(Destination.destination_id == destination_id))
        if not dest:
            return False

        # Datos de usuarios (Favoritos, Reseñas, Visitas, Rankings)
        db.query(Favorite).filter(Favorite.destination_id == destination_id).delete(synchronize_session=False)
        db.query(Review).filter(Review.destination_id == destination_id).delete(synchronize_session=False)
        db.query(Visit).filter(Visit.destination_id == destination_id).delete(synchronize_session=False)
        db.query(ContextualRanking).filter(ContextualRanking.destination_id == destination_id).delete(synchronize_session=False)

        # Multimedia
        db.query(DestinationMedia).filter(DestinationMedia.destination_id == destination_id).delete(synchronize_session=False)

        # Scores y métricas
        db.query(DestinationAspectScore).filter(DestinationAspectScore.destination_id == destination_id).delete(synchronize_session=False)
        db.query(ClimateScore).filter(ClimateScore.destination_id == destination_id).delete(synchronize_session=False)
        db.query(CrowdScore).filter(CrowdScore.destination_id == destination_id).delete(synchronize_session=False)

        # Catálogo
        db.query(TourismCatalog).filter(TourismCatalog.destination_id == destination_id).delete(synchronize_session=False)

        # Destino principal
        db.query(Destination).filter(Destination.destination_id == destination_id).delete(synchronize_session=False)

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando destino {destination_id}: {e}")
        raise e
