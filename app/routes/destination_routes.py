"""
PROXVEL Backend - Destination Routes.
Endpoints para listar y consultar destinos turísticos.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.services import destination_context_service, destination_service
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
    db: Session = Depends(get_db)
):
    """Lista destinos disponibles con filtros opcionales."""
    destinations = destination_service.get_destinations(db=db, city=city, limit=limit)
    return success_response(
        data=destinations,
        message="Destinos obtenidos correctamente",
    )


@router.get(
    "/month-context",
    summary="Clima y afluencia de todos los destinos en un mes",
    description=(
        "Datos de la tesis (Fase 4) por destino para el mes pedido: puntaje de clima por "
        "preferencia (favorable >= 0.70), riesgos y nivel de afluencia. Alimenta los filtros "
        "de clima y afluencia del buscador. No modifica el motor."
    ),
)
def month_context(
    month: int = Query(..., ge=1, le=12, description="Mes (1-12)"),
    db: Session = Depends(get_db),
):
    items = destination_context_service.month_context(db, month)
    return success_response(data=items, message="Contexto mensual obtenido correctamente", count=len(items))


@router.get(
    "/{destination_id}/calendar",
    summary="Calendario de 12 meses de un destino",
    description=(
        "Clima (según la preferencia) y aforo (según la tolerancia) mes a mes, con la explicación "
        "de la tesis y el mejor/peor mes. Sin parámetros usa clima indiferente y tolerancia media."
    ),
)
def destination_calendar(
    destination_id: str,
    clima: str | None = Query(None, description="frio | templado | calido | seco | indiferente"),
    tolerancia: str | None = Query(None, description="baja | media | alta"),
    db: Session = Depends(get_db),
):
    data = destination_context_service.calendar(db, destination_id, clima, tolerancia)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Destino no encontrado: {destination_id}")
    return success_response(data=data, message="Calendario obtenido correctamente")


@router.get(
    "/{destination_id}",
    summary="Detalle de destino",
    description=(
        "Devuelve el detalle completo de un destino, incluyendo "
        "puntajes ABSA por aspecto y contexto climático/aforo. "
        "El parámetro month (1-12) selecciona el mes del contexto; "
        "sin él se usa el último disponible."
    ),
)
def get_destination(
    destination_id: str,
    month: int | None = Query(
        None, ge=1, le=12, description="Mes (1-12) para clima/aforo"
    ),
    db: Session = Depends(get_db)
):
    """Obtiene detalle de un destino por su ID (slug)."""
    detail = destination_service.get_destination_detail(db, destination_id, month=month)

    if detail is None:
        raise HTTPException(
            status_code=404,
            detail=f"Destino no encontrado: {destination_id}",
        )

    return success_response(
        data=detail,
        message="Detalle de destino obtenido correctamente",
    )
