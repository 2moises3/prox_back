"""
PROXVEL Backend - Recommendation Routes.
Endpoints de ranking contextual, búsqueda y recomendaciones base.
"""

from fastapi import APIRouter, Query, Depends, HTTPException

from app.core.security import get_current_user
from app.schemas.user_schema import UserResponse
from app.schemas.recommendation_schema import RecommendationMeResponse
from app.services import (
    contextual_ranking_service,
    recommendation_service,
    recommendation_engine_v0,
    traveler_profile_service
)
from app.utils.response_builder import success_response

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])

@router.get(
    "/me",
    summary="Recomendaciones dinámicas para usuario autenticado",
    description=(
        "Endpoint protegido que genera recomendaciones en tiempo real "
        "usando el traveler_profile orgánico del usuario, cruzado con la matriz ABSA."
    ),
    response_model=RecommendationMeResponse,
)
def get_my_recommendations(
    limit: int = Query(10, ge=1, le=100, description="Límite de resultados"),
    current_user: UserResponse = Depends(get_current_user),
):
    """Genera recomendaciones matemáticas on-the-fly para el usuario autenticado."""
    # 1. Extraer perfil de viaje
    profile, error = traveler_profile_service.get_profile_by_user_id(current_user.user_id)
    if error or not profile:
        raise HTTPException(
            status_code=400,
            detail="El usuario no cuenta con un perfil de viaje. Completa el Onboarding primero."
        )

    # 2. Computar recomendaciones usando motor dinámico V0
    results = recommendation_engine_v0.generate_recommendations(
        user_profile=profile.model_dump(),
        limit=limit
    )

    # 3. Retornar contrato estricto
    return RecommendationMeResponse(
        success=True,
        message="Recomendaciones personalizadas generadas correctamente",
        engine={
            "source": "engine_v0",
            "version": "0.1",
            "is_final_model": False,
            "metrics_status": "en_mejora"
        },
        data=results
    )


@router.get(
    "/contextual",
    summary="Ranking contextual final",
    description=(
        "Devuelve el ranking contextual final desde Fase 4. "
        "Incluye re-ranking con clima y aforo. "
        "Si no se indica user_id, devuelve datos del primer usuario como demo."
    ),
)
def contextual_ranking(
    user_id: str | None = Query(
        None, description="ID del usuario (ej: U00001)"
    ),
    city: str | None = Query(
        None, description="Filtrar por ciudad (preparado para futuro)"
    ),
    limit: int = Query(10, ge=1, le=100, description="Límite de resultados"),
):
    """Obtiene ranking contextual con filtros opcionales."""
    results = contextual_ranking_service.get_contextual_ranking(
        user_id=user_id, city=city, limit=limit,
    )
    return success_response(
        data=results,
        message="Ranking contextual obtenido correctamente",
    )


@router.get(
    "/search",
    summary="Búsqueda de destinos",
    description=(
        "Busca destinos por texto o ciudad en los datos de ranking. "
        "Los resultados se ordenan por compatibilidad descendente."
    ),
)
def search_recommendations(
    query: str | None = Query(
        None, description="Texto de búsqueda (nombre de destino)"
    ),
    city: str | None = Query(
        None, description="Filtrar por ciudad (preparado para futuro)"
    ),
    limit: int = Query(10, ge=1, le=100, description="Límite de resultados"),
):
    """Busca destinos por texto o ciudad."""
    results = recommendation_service.search(
        query=query, city=city, limit=limit,
    )
    return success_response(
        data=results,
        message="Resultados de búsqueda obtenidos correctamente",
    )


@router.get(
    "/base",
    summary="Recomendaciones base (Fase 3)",
    description=(
        "Endpoint preparado para recomendaciones base de afinidad "
        "destino-perfil (Fase 3). Actualmente en estado parcial. "
        "Los datos de score_fase3 están disponibles vía /contextual."
    ),
)
def base_recommendations():
    """
    Devuelve información sobre disponibilidad de recomendaciones base.
    Este endpoint queda como stub documentado hasta que se integre
    un archivo CSV independiente de Fase 3.
    """
    result = recommendation_service.get_base_recommendations()
    return result
