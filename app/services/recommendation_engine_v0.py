"""
PROXVEL Backend - Engine V0 para Recomendaciones Dinámicas.
Implementa WSM (Weighted Sum Model) en tiempo real para usuarios autenticados.

Fuente de datos: tabla destination_aspect_scores (PostgreSQL).
Fallback: matriz_absa_normalizada.csv si la BD no tiene filas aún.
Destinos sin puntajes ABSA reciben un score neutro de 0.5 por aspecto.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select

from app.config.database import SessionLocal
from app.models.aspect_score_model import DestinationAspectScore
from app.models.destination_model import Destination
from app.repositories import db_tourism_repository, db_ranking_repository
from app.repositories.csv_loader import get_data
from app.utils.normalizers import generate_destination_id, safe_float

logger = logging.getLogger(__name__)

_ABSA_ASPECTS = [
    "accesibilidad", "aforo_multitudes", "alojamiento", "atencion_servicio",
    "atractivos", "clima", "costos", "gastronomia", "limpieza", "seguridad",
]
_NEUTRAL_SCORE = 0.5  # score por defecto para destinos sin ABSA registrado


def _wsm(weights: dict[str, float], total_weight: float, scores: dict[str, float]) -> tuple[float, list[dict]]:
    """Calcula WSM y devuelve (weighted_sum, top_aspects)."""
    top_aspects = []
    weighted_sum = 0.0
    for aspect, user_weight in weights.items():
        dest_score = scores.get(aspect, _NEUTRAL_SCORE)
        contribution = (user_weight * dest_score) / total_weight
        weighted_sum += contribution
        top_aspects.append({
            "aspect": aspect,
            "user_weight": round(user_weight, 2),
            "destination_score": round(dest_score, 4),
            "contribution": round(contribution, 4),
        })
    top_aspects.sort(key=lambda x: x["contribution"], reverse=True)
    return weighted_sum, top_aspects


def generate_recommendations(user_profile: dict[str, Any], limit: int = 10) -> list[dict[str, Any]]:
    # 1. Extraer pesos del perfil de viaje
    weights = {
        "accesibilidad": safe_float(user_profile.get("peso_accesibilidad"), 3.0),
        "aforo_multitudes": safe_float(user_profile.get("peso_aforo_multitudes"), 3.0),
        "alojamiento": safe_float(user_profile.get("peso_alojamiento"), 3.0),
        "atencion_servicio": safe_float(user_profile.get("peso_atencion_servicio"), 3.0),
        "atractivos": safe_float(user_profile.get("peso_atractivos"), 3.0),
        "clima": safe_float(user_profile.get("peso_clima"), 3.0),
        "costos": safe_float(user_profile.get("peso_costos"), 3.0),
        "gastronomia": safe_float(user_profile.get("peso_gastronomia"), 3.0),
        "limpieza": safe_float(user_profile.get("peso_limpieza"), 3.0),
        "seguridad": safe_float(user_profile.get("peso_seguridad"), 3.0),
    }

    total_weight = sum(weights.values()) or 1.0

    scored_destinations = []
    current_month = datetime.now().month

    db = SessionLocal()
    try:
        # 2. Cargar destinos activos + sus puntajes ABSA en una sola consulta (sin N+1)
        stmt = (
            select(Destination, DestinationAspectScore)
            .outerjoin(
                DestinationAspectScore,
                Destination.destination_id == DestinationAspectScore.destination_id,
            )
            .where(Destination.is_active.is_(True))
        )
        db_rows = db.execute(stmt).all()

        if db_rows:
            # Ruta principal: datos vivos de PostgreSQL
            logger.info("Engine V0: %d destinos activos desde BD.", len(db_rows))
            for dest, scores_row in db_rows:
                destination_id = dest.destination_id
                destination_name = dest.destination

                # Construir dict de puntajes; None → neutral
                scores: dict[str, float] = {}
                for aspect in _ABSA_ASPECTS:
                    raw = getattr(scores_row, aspect, None) if scores_row else None
                    scores[aspect] = raw if raw is not None else _NEUTRAL_SCORE

                has_real_scores = scores_row is not None and any(
                    getattr(scores_row, a) is not None for a in _ABSA_ASPECTS
                )

                weighted_sum, top_aspects = _wsm(weights, total_weight, scores)
                context = db_ranking_repository._get_month_context(db, destination_id, current_month)
                enrichment = db_tourism_repository.get_enrichment_data(destination_id, db=db)

                best_aspects_names = [a["aspect"] for a in top_aspects[:3]]
                summary = f"Alta afinidad por {', '.join(best_aspects_names)}."
                if not has_real_scores:
                    summary = "Puntajes en construcción — compatibilidad estimada."

                scored_destinations.append({
                    "destination_id": destination_id,
                    "name": destination_name,
                    "city": enrichment.get("city") if enrichment else None,
                    "region": enrichment.get("region") if enrichment else None,
                    "category": enrichment.get("category") if enrichment else None,
                    "cover_image_url": enrichment.get("cover_image_url") if enrichment else None,
                    "compatibility_score": round(weighted_sum, 4),
                    "compatibility_percent": int(round(weighted_sum * 100)),
                    "has_real_scores": has_real_scores,
                    "context_status": context.get("weather_category") or "verde",
                    "explanation": {
                        "summary": summary,
                        "top_aspects": top_aspects[:3],
                    },
                })

        else:
            # Fallback: CSV estático (mientras BD esté vacía / antes del seed)
            absa_data = get_data("absa") or []
            if not absa_data:
                logger.error("Engine V0: BD vacía y CSV ABSA no cargado.")
                return []

            logger.warning("Engine V0: Fallback a CSV (%d filas). Ejecuta seed_absa_scores.py.", len(absa_data))
            for row in absa_data:
                destination_name = row.get("destination", "")
                if not destination_name:
                    continue
                destination_id = generate_destination_id(destination_name)
                scores = {a: safe_float(row.get(a), _NEUTRAL_SCORE) for a in _ABSA_ASPECTS}
                weighted_sum, top_aspects = _wsm(weights, total_weight, scores)
                context = db_ranking_repository._get_month_context(db, destination_id, current_month)
                enrichment = db_tourism_repository.get_enrichment_data(destination_id, db=db)
                best_aspects_names = [a["aspect"] for a in top_aspects[:3]]
                scored_destinations.append({
                    "destination_id": destination_id,
                    "name": destination_name,
                    "city": enrichment.get("city") if enrichment else None,
                    "region": enrichment.get("region") if enrichment else None,
                    "category": enrichment.get("category") if enrichment else None,
                    "cover_image_url": enrichment.get("cover_image_url") if enrichment else None,
                    "compatibility_score": round(weighted_sum, 4),
                    "compatibility_percent": int(round(weighted_sum * 100)),
                    "has_real_scores": True,
                    "context_status": context.get("weather_category") or "verde",
                    "explanation": {
                        "summary": f"Alta afinidad por {', '.join(best_aspects_names)}.",
                        "top_aspects": top_aspects[:3],
                    },
                })

    finally:
        db.close()

    # 3. Ordenar y asignar posición
    scored_destinations.sort(key=lambda x: x["compatibility_score"], reverse=True)
    for idx, dest in enumerate(scored_destinations):
        dest["ranking_position"] = idx + 1

    return scored_destinations[:limit]
