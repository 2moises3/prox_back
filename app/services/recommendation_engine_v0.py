"""
PROXVEL Backend - Engine V0 para Recomendaciones Dinámicas.
Implementa WSM (Weighted Sum Model) en tiempo real para usuarios autenticados.
"""

import logging
from datetime import datetime
from typing import Any

from app.config.database import SessionLocal
from app.repositories.csv_loader import get_data
from app.repositories import db_tourism_repository, db_ranking_repository
from app.utils.normalizers import generate_destination_id, safe_float

logger = logging.getLogger(__name__)

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

    total_weight = sum(weights.values())
    if total_weight <= 0:
        total_weight = 1.0

    # 2. Cargar Matriz ABSA estática cacheada
    absa_data = get_data("absa")
    if not absa_data:
        logger.error("Engine V0: Matriz ABSA no cargada.")
        return []

    scored_destinations = []
    current_month = datetime.now().month

    db = SessionLocal()
    try:
        # 3. Calcular Score Base por Destino (WSM)
        for row in absa_data:
            destination_name = row.get("destination", "")
            if not destination_name:
                continue
                
            destination_id = generate_destination_id(destination_name)
            
            weighted_sum = 0.0
            top_aspects = []
            
            for aspect, user_weight in weights.items():
                dest_score = safe_float(row.get(aspect), 0.0)
                # Maximizamos: peso * score
                # Multiplicamos por (1/total_weight) para normalizar a 0-1
                contribution = (user_weight * dest_score) / total_weight
                weighted_sum += contribution
                
                top_aspects.append({
                    "aspect": aspect,
                    "user_weight": round(user_weight, 2),
                    "destination_score": round(dest_score, 4),
                    "contribution": round(contribution, 4)
                })
                
            # Ordenar los mejores aspectos de este destino para el usuario
            top_aspects.sort(key=lambda x: x["contribution"], reverse=True)
            
            # Obtener contexto actual (Clima y Aforo) de PostgreSQL
            context = db_ranking_repository._get_month_context(db, destination_id, current_month)
            
            # TODO (Fase 4 interna): Integración matemática estricta del contexto (B_contextual, P_contextual).
            # Por el momento, en engine_v0 usamos el compatibility_score puramente como la suma WSM,
            # lo que ya es un salto enorme desde el mock.
            final_score = weighted_sum
            
            # Resumen de explicación
            best_aspects_names = [a["aspect"] for a in top_aspects[:3]]
            summary = f"Alta afinidad por {', '.join(best_aspects_names)}."

            # Enriquecer con el catálogo oficial
            enrichment = db_tourism_repository.get_enrichment_data(destination_id, db=db)
            
            item = {
                "destination_id": destination_id,
                "name": destination_name,
                "city": enrichment.get("city") if enrichment else None,
                "region": enrichment.get("region") if enrichment else None,
                "category": enrichment.get("category") if enrichment else None,
                "cover_image_url": enrichment.get("cover_image_url") if enrichment else None,
                "rating": 4.5, # Rating genérico si no hay reales
                "compatibility_score": round(final_score, 4),
                "compatibility_percent": int(round(final_score * 100)),
                "context_status": "verde" if not context.get("weather_category") else context.get("weather_category"),
                "explanation": {
                    "summary": summary,
                    "top_aspects": top_aspects[:3] # Solo enviamos los top 3 para ahorrar payload
                }
            }
            scored_destinations.append(item)
            
    finally:
        db.close()

    # 4. Ordenar y retornar
    scored_destinations.sort(key=lambda x: x["compatibility_score"], reverse=True)
    
    # Asignar posición de ranking
    for idx, dest in enumerate(scored_destinations):
        dest["ranking_position"] = idx + 1

    return scored_destinations[:limit]
