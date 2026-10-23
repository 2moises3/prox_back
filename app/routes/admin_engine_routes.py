"""
PROXVEL Backend - Admin Engine Routes.
Control del motor de recomendación desde el dashboard.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.security import require_admin_or_super_admin, require_super_admin
from app.schemas.engine_schema import EngineConfigUpdate, EngineMembershipUpdate
from app.schemas.user_schema import UserResponse
from app.services import engine_admin_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/admin/engine", tags=["Admin - Motor"])


def _status_payload(db: Session) -> dict:
    dests = engine_admin_service.universe(db)
    from app.services.thesis_engine import get_engine, VERSION
    engine = get_engine()
    return {
        "version": VERSION,
        "read_only": True,
        "aspects": engine.aspects,
        "profile_weights": engine.profile_weights,
        "config": engine_admin_service.get_config(db),
        "defaults": engine_admin_service.get_defaults(),
        "destinations": dests,
        "counts": {
            "total": len(dests),
            "in_engine": sum(1 for d in dests if d["in_engine"]),
            "recommendable": sum(1 for d in dests if d["recommendable"]),
        },
    }


@router.get("", summary="Parámetros del motor y destinos que participan")
def get_engine(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin_or_super_admin),
):
    return success_response(data=_status_payload(db), message="Estado del motor obtenido")


@router.put("/config", summary="Actualizar parámetros del motor (solo super_admin)")
def put_engine_config(
    payload: EngineConfigUpdate,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_super_admin),
):
    engine_admin_service.update_config(db, payload.model_dump())
    return success_response(data=_status_payload(db), message="Parámetros del motor actualizados")


@router.post("/config/reset", summary="Restablecer parámetros a los valores de la tesis (solo super_admin)")
def reset_engine_config(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_super_admin),
):
    engine_admin_service.update_config(db, engine_admin_service.get_defaults())
    return success_response(data=_status_payload(db), message="Parámetros restablecidos a los valores de la tesis")


@router.patch("/destinations/{destination_id}", summary="Incluir o excluir un destino del motor")
def patch_destination_engine(
    destination_id: str,
    payload: EngineMembershipUpdate,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin_or_super_admin),
):
    result, error = engine_admin_service.set_in_engine(db, destination_id, payload.in_engine)
    if error == "not_found":
        raise HTTPException(status_code=404, detail=f"Destino no encontrado: {destination_id}")
    if error:
        raise HTTPException(status_code=400, detail=error)
    msg = "Destino incluido en el motor" if payload.in_engine else "Destino excluido del motor"
    return success_response(data=result, message=msg)
