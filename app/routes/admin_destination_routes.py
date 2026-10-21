"""
PROXVEL Backend - Admin Destination Routes.
Endpoints administrativos para gestionar información y multimedia de destinos.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
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
from app.services import (
    content_seed_service,
    destination_service,
    destination_media_service,
    destination_metric_sync_service,
    destination_merge_service,
)
from app.utils.response_builder import success_response

router = APIRouter(prefix="/admin/destinations", tags=["Admin Destinations"])
audit_logger = logging.getLogger("proxvel.audit")


class ContentLoadRequest(BaseModel):
    # False: solo completa campos vacíos. True: reemplaza lo existente (solo super_admin).
    overwrite: bool = False


@router.post("/content/load", summary="Cargar la ficha comercial de los destinos desde el archivo de datos")
def load_destination_content(
    payload: ContentLoadRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_or_super_admin),
):
    if payload.overwrite and current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Solo un super_admin puede sobrescribir datos existentes.")
    try:
        result = content_seed_service.load_content(db, overwrite=payload.overwrite)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No se encontró seed_data/destination_content.json en el servidor.")
    audit_logger.info("AUDIT destination_content_load user=%s overwrite=%s updated=%s fields=%s",
                      current_admin.user_id, payload.overwrite,
                      result["destinations_updated"], result["fields_written"])
    return success_response(data=result, message="Contenido de destinos cargado")


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


# ── Detalle destino admin (incluye inactivos) ───────────────────────────────

@router.get("/{destination_id}", summary="Detalle de destino (admin)")
def get_destination_admin(
    destination_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_or_super_admin),
):
    detail = destination_service.get_destination_detail(db, destination_id, include_inactive=True)
    if detail is None:
        raise HTTPException(
            status_code=404,
            detail=f"Destino no encontrado: {destination_id}",
        )
    return success_response(
        data=detail,
        message="Detalle de destino (admin) obtenido correctamente",
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


# ── Sincronizar desde Métricas (NUEVO FLUJO OFICIAL) ─────────────────────────

@router.post("/sync-from-metrics", summary="Recalcula data_status de todos los destinos desde la BD")
def sync_from_metrics(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_or_super_admin),
):
    # En un entorno estricto, esto debería ser solo super_admin
    # pero usamos el mismo check de rutas admin.
    result = destination_metric_sync_service.sync_destinations_from_metrics(db)
    return success_response(data=result, message="Sincronización completada")


# ── Activar / desactivar destino ──────────────────────────────────────────────

@router.patch("/{destination_id}/status", summary="Activar o desactivar un destino")
def set_destination_status(
    destination_id: str,
    payload: DestinationStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_or_super_admin),
):
    if payload.is_active:
        # Validaciones de reglas de negocio para activación
        from app.models.tourism_catalog_model import TourismCatalog
        catalog = db.query(TourismCatalog).filter(TourismCatalog.destination_id == destination_id).first()
        
        if not catalog:
            raise HTTPException(status_code=400, detail="El destino no tiene registro en el catálogo.")
            
        if catalog.data_status == "out_of_engine":
            raise HTTPException(
                status_code=400,
                detail="No se puede activar: el destino no tiene puntajes ABSA. "
                       "Importa los puntajes desde el dashboard primero.",
            )

        if not all([catalog.city, catalog.region, catalog.category, catalog.description]):
            raise HTTPException(
                status_code=400,
                detail="No se puede activar: faltan campos editoriales obligatorios "
                       "(ciudad, región, categoría, descripción).",
            )

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


# ── Fusionar destino (elimina source, conserva target) ───────────────────────

@router.post(
    "/{source_id}/merge-into/{target_id}",
    summary="Fusiona el destino origen en el destino canónico y elimina el origen",
)
def merge_destination(
    source_id: str,
    target_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_or_super_admin),
):
    result = destination_merge_service.merge_destinations(db, source_id, target_id)
    return success_response(
        data=result,
        message=f"Fusión completada. '{source_id}' eliminado, datos migrados a '{target_id}'.",
    )


# ── Eliminar destino permanentemente ──────────────────────────────────────────

@router.delete("/{destination_id}", summary="Eliminar destino permanentemente")
def delete_destination(
    destination_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_or_super_admin),
):
    from app.repositories import db_destination_repository
    success = db_destination_repository.delete_destination_admin(db, destination_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Destino no encontrado: {destination_id}")
    return success_response(data=None, message="Destino y todos sus datos eliminados permanentemente")
