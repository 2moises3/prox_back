"""
PROXVEL Backend - Destination Routes.
Endpoints para listar y consultar destinos turísticos.
"""

from fastapi import APIRouter, HTTPException, Query

from app.services import destination_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/destinations", tags=["Destinations"])


@router.get(
    "",
    summary="Listar destinos",
    description=(
        "Devuelve los destinos turísticos detectados en los CSV de tesis. "
        "Soporta filtro por ciudad y límite de resultados."
    ),
)
def list_destinations(
    city: str | None = Query(
        None, description="Filtrar por ciudad (parcial, case-insensitive)"
    ),
    limit: int = Query(50, ge=1, le=200, description="Límite de resultados"),
):
    """Lista destinos disponibles con filtros opcionales."""
    destinations = destination_service.get_destinations(city=city, limit=limit)
    return success_response(
        data=destinations,
        message="Destinos obtenidos correctamente",
    )


@router.get(
    "/{destination_id}",
    summary="Detalle de destino",
    description=(
        "Devuelve el detalle completo de un destino, incluyendo "
        "puntajes ABSA por aspecto y contexto climático/aforo."
    ),
)
def get_destination(destination_id: str):
    """Obtiene detalle de un destino por su ID (slug)."""
    detail = destination_service.get_destination_detail(destination_id)

    if detail is None:
        raise HTTPException(
            status_code=404,
            detail=f"Destino no encontrado: {destination_id}",
        )

    return success_response(
        data=detail,
        message="Detalle de destino obtenido correctamente",
    )
