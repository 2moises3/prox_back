"""
PROXVEL Backend - DB Ranking Repository.
Acceso a datos de ranking contextual desde PostgreSQL con fallback a CSV.
"""

import logging
from typing import Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from app.config.database import SessionLocal
from app.repositories import ranking_repository as fallback_repo
from app.repositories import db_tourism_repository
from app.models.contextual_ranking_model import ContextualRanking
from app.models.destination_model import Destination

logger = logging.getLogger(__name__)


def get_contextual_ranking(user_id: str | None = None, city: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    try:
        db = SessionLocal()
        try:
            if db.query(ContextualRanking).count() == 0:
                logger.info("PostgreSQL: Tabla contextual_rankings vacía. Fallback a CSV.")
                return fallback_repo.get_contextual_ranking(user_id=user_id, city=city, limit=limit)

            logger.info("PostgreSQL: Leyendo contextual_rankings.")
            
            # Si no hay user_id, buscar el primero disponible
            target_user_id = user_id
            if not target_user_id:
                first_user = db.scalar(select(ContextualRanking.user_id).order_by(ContextualRanking.user_id).limit(1))
                target_user_id = first_user

            if not target_user_id:
                return []

            query = (
                select(ContextualRanking)
                .options(joinedload(ContextualRanking.destination_rel))
                .where(ContextualRanking.user_id == target_user_id)
                .order_by(ContextualRanking.rank)
            )
            rankings_db = db.scalars(query).all()

            results = []
            for r in rankings_db:
                dest_name = r.destination_rel.destination if r.destination_rel else None
                item = {
                    "rank": r.rank,
                    "destination_id": r.destination_id,
                    "destination": dest_name,
                    "city": None,
                    "region": None,
                    "category": None,
                    "cover_image_url": None,
                    "compatibility_percentage": r.compatibilidad_final,
                    "label": r.etiqueta_final,
                    "final_score": r.score_final_fase4,
                    "short_explanation": r.explicacion_final,
                    "aspect_scores": None,
                    "context": {
                        "weather_score": None, # Los scores de contexto no están en ContextualRanking per se
                        "crowd_score": None,   # Pero el CSV original los traía pre-joinados
                        "weather_category": None,
                        "crowd_level": None,
                    },
                    "tourism_summary": None,
                }
                
                enrichment = db_tourism_repository.get_enrichment_data(r.destination_id, db=db)
                if enrichment:
                    item["city"] = enrichment.get("city")
                    item["region"] = enrichment.get("region")
                    item["category"] = enrichment.get("category")
                    item["cover_image_url"] = enrichment.get("cover_image_url")
                    item["tourism_summary"] = {
                        "description": enrichment.get("description"),
                        "experience_type": enrichment.get("experience_type"),
                        "cover_image_url": enrichment.get("cover_image_url"),
                    }
                
                results.append(item)

            if city:
                results = [r for r in results if r.get("city") and city.lower() in r["city"].lower()]

            return results[:limit]
        finally:
            db.close()
    except Exception as e:
        logger.error("PostgreSQL fallback activado en get_contextual_ranking: %s", e)
        return fallback_repo.get_contextual_ranking(user_id=user_id, city=city, limit=limit)


def search_recommendations(query: str | None = None, city: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    try:
        db = SessionLocal()
        try:
            if db.query(ContextualRanking).count() == 0:
                logger.info("PostgreSQL: Tabla contextual_rankings vacía. Fallback a CSV.")
                return fallback_repo.search_recommendations(query=query, city=city, limit=limit)

            logger.info("PostgreSQL: Buscando recomendaciones en contextual_rankings.")
            
            # Buscar el mejor ranking por destino
            # Una forma eficiente en Postgres es DISTINCT ON, o iterando
            # Para mantener compatibilidad estricta con sqlite/otras, hacemos deduplicación en Python:
            all_rankings = db.scalars(
                select(ContextualRanking)
                .options(joinedload(ContextualRanking.destination_rel))
            ).all()

            seen = {}
            for r in all_rankings:
                dest_id = r.destination_id
                if dest_id not in seen:
                    seen[dest_id] = r
                else:
                    if r.compatibilidad_final and seen[dest_id].compatibilidad_final:
                        if r.compatibilidad_final > seen[dest_id].compatibilidad_final:
                            seen[dest_id] = r

            unique_rows = list(seen.values())

            if query:
                q_lower = query.lower()
                unique_rows = [
                    r for r in unique_rows
                    if r.destination_rel and r.destination_rel.destination and q_lower in r.destination_rel.destination.lower()
                ]

            unique_rows.sort(key=lambda x: x.compatibilidad_final or 0, reverse=True)

            results = []
            for r in unique_rows[:limit]:
                dest_name = r.destination_rel.destination if r.destination_rel else None
                enrichment = db_tourism_repository.get_enrichment_data(r.destination_id, db=db)
                
                item = {
                    "destination_id": r.destination_id,
                    "destination": dest_name,
                    "city": enrichment.get("city") if enrichment else None,
                    "region": enrichment.get("region") if enrichment else None,
                    "category": enrichment.get("category") if enrichment else None,
                    "cover_image_url": enrichment.get("cover_image_url") if enrichment else None,
                    "compatibility_percentage": r.compatibilidad_final,
                    "final_score": r.score_final_fase4,
                }
                results.append(item)

            if city:
                results = [r for r in results if r.get("city") and city.lower() in r["city"].lower()]

            return results
        finally:
            db.close()
    except Exception as e:
        logger.error("PostgreSQL fallback activado en search_recommendations: %s", e)
        return fallback_repo.search_recommendations(query=query, city=city, limit=limit)
