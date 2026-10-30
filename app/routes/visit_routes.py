"""
PROXVEL Backend - Visit & Atlas Routes.
Endpoints para check-in de presencia GPS, certificación de visitas y consulta del Atlas.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.security import get_current_user
from app.schemas.user_schema import UserResponse
from app.schemas.visit_schema import (
    CheckInRequest,
    VerifyVisitRequest,
)
from app.services import visit_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/visits", tags=["Visits"])


@router.post(
    "/check-in",
    summary="Registrar check-in de visita",
    description="Inicia o consulta la visita activa del usuario en un destino turístico validando proximidad GPS.",
    response_model=dict,
)
def check_in(
    request: CheckInRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result, error, code = visit_service.check_in_visit(
        user_id=current_user.user_id,
        destination_id=request.destination_id,
        latitude=request.latitude,
        longitude=request.longitude,
        db=db,
    )
    if error:
        raise HTTPException(status_code=code, detail=error)

    message = (
        "Visita en progreso recuperada."
        if code == 200
        else "Check-in registrado con éxito. ¡Disfruta tu recorrido!"
    )
    return success_response(data=result, message=message)


@router.post(
    "/verify",
    summary="Certificar visita completada",
    description="Sella la visita en el Atlas del usuario una vez cumplido el tiempo mínimo de permanencia.",
    response_model=dict,
)
def verify_visit(
    request: VerifyVisitRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result, error, code = visit_service.verify_visit(
        user_id=current_user.user_id,
        visit_id=request.visit_id,
        latitude=request.latitude,
        longitude=request.longitude,
        db=db,
    )
    if error:
        raise HTTPException(status_code=code, detail=error)

    return success_response(
        data=result,
        message="¡Felicidades! Tu visita ha sido validada y sellada en tu Atlas.",
    )


@router.get(
    "/active",
    summary="Obtener visita activa en progreso",
    description="Devuelve el estado de la visita actual en curso para el usuario autenticado, si existe.",
    response_model=dict,
)
def get_active_visit(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    active = visit_service.get_active_visit(current_user.user_id, db=db)
    return success_response(
        data=active,
        message="Visita activa obtenida con éxito.",
    )


@router.get(
    "/atlas",
    summary="Consultar Atlas de Visitas del usuario",
    description="Devuelve todos los sellos de destinos turísticos verificados por el usuario autenticado.",
    response_model=dict,
)
def get_user_atlas(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    atlas = visit_service.get_user_atlas(current_user.user_id, db=db)
    return success_response(
        data=atlas,
        message="Atlas de visitas obtenido con éxito.",
    )
