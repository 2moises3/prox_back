"""
PROXVEL Backend - Admin Destination Routes.
Endpoints administrativos para gestionar información y multimedia de destinos.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.security import require_admin_or_super_admin
from app.models.user_model import User
from app.schemas.destination_schema import (
    AbsaScoresUpdate,
    DestinationAdminUpdate,
    DestinationAdminCreate,
    DestinationCreateResponse,
    DestinationDetail,
    DestinationStatusUpdate,
)
from app.services import destination_service, destination_media_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/admin/destinations", tags=["Admin Destinations"])


# ── Listar destinos (incluye inactivos) ───────────────────────────────────────

@router.get("", summary="Listar destinos (incluye inactivos)")
def list_destinations_admin(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_or_super_admin),
):
    destinations = destination_service.get_destinations(db, limit=200, include_inactive=True)
    return success_response(
        data=[d.model_dump() for d in destinations],
        message="Destinos (admin) obtenidos correctamente",
    )


# ── Crear destino ─────────────────────────────────────────────────────────────

@router.post("", summary="Crear destino")
def create_destination(
    payload: DestinationAdminCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_or_super_admin),
):
    try:
        created = destination_service.create_destination_admin(db, payload.model_dump())
        return success_response(data=DestinationCreateResponse(**created), message="Destino creado correctamente")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado: {e}")


# ── Editar destino ────────────────────────────────────────────────────────────

@router.patch("/{destination_id}", summary="Actualizar información de destino")
def update_destination(
    destination_id: str,
    update_data: DestinationAdminUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_or_super_admin),
):
    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        raise HTTPException(status_code=422, detail="Se requiere al menos un campo para actualizar.")
    try:
        updated = destination_service.update_destination_admin(db, destination_id, update_dict)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Destino no encontrado: {destination_id}")
        return success_response(data=updated, message="Destino actualizado correctamente")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado: {e}")


# ── Activar / desactivar destino ──────────────────────────────────────────────

@router.patch("/{destination_id}/status", summary="Activar o desactivar un destino")
def set_destination_status(
    destination_id: str,
    payload: DestinationStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_or_super_admin),
):
    updated = destination_service.set_destination_status(db, destination_id, payload.is_active)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Destino no encontrado: {destination_id}")
    estado = "activado" if payload.is_active else "desactivado"
    return success_response(data=updated, message=f"Destino {estado} correctamente")


# ── Puntajes ABSA ────────────────────────────────────────────────────────────

@router.patch("/{destination_id}/absa-scores", summary="Actualizar puntajes ABSA del destino")
def update_absa_scores(
    destination_id: str,
    payload: AbsaScoresUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_or_super_admin),
):
    scores = payload.model_dump(exclude_unset=True)
    if not scores:
        raise HTTPException(status_code=422, detail="Se requiere al menos un puntaje.")
    updated = destination_service.update_absa_scores(db, destination_id, scores)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Destino no encontrado: {destination_id}")
    return success_response(data=updated, message="Puntajes ABSA actualizados correctamente")


# ── Multimedia admin (incluye inactivos) ──────────────────────────────────────

@router.get("/{destination_id}/media", summary="Toda la multimedia del destino (incl. inactivos)")
def get_all_media(
    destination_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_or_super_admin),
):
    result = destination_media_service.get_all_destination_media(db, destination_id)
    return success_response(data=result.model_dump(), message="Multimedia obtenida")


# ── Eliminar imagen permanentemente ──────────────────────────────────────────

@router.delete("/{destination_id}/media/{media_id}/permanent", summary="Eliminar imagen permanentemente")
def permanent_delete_media(
    destination_id: str,
    media_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_or_super_admin),
):
    success = destination_media_service.permanent_delete_media(db, media_id)
    if not success:
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return success_response(data=None, message="Imagen eliminada permanentemente")
