"""
PROXVEL Backend - Admin Announcement Routes.
CRUD de anuncios internos. Protegido con require_admin_or_super_admin.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.security import require_admin_or_super_admin
from app.schemas.user_schema import UserResponse
from app.schemas.announcement_schema import AnnouncementCreate, AnnouncementUpdate
from app.services import announcement_service, cloudinary_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/admin/announcements", tags=["Admin - Anuncios"])


@router.get("", summary="Listar anuncios internos")
def list_announcements(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    items = announcement_service.list_announcements(db)
    return success_response(
        data=[i.model_dump() for i in items],
        message="Anuncios obtenidos correctamente",
    )


@router.post("", summary="Crear anuncio interno", status_code=201)
def create_announcement(
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    created = announcement_service.create_announcement(
        db, payload, created_by=current_user.user_id
    )
    return success_response(data=created.model_dump(), message="Anuncio creado correctamente")


@router.get("/{announcement_id}", summary="Detalle de anuncio")
def get_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    item = announcement_service.get_announcement(db, announcement_id)
    if not item:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    return success_response(data=item.model_dump(), message="Anuncio obtenido correctamente")


@router.patch("/{announcement_id}", summary="Actualizar anuncio")
def update_announcement(
    announcement_id: int,
    payload: AnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    try:
        updated = announcement_service.update_announcement(db, announcement_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    return success_response(data=updated.model_dump(), message="Anuncio actualizado correctamente")


@router.delete("/{announcement_id}", summary="Eliminar anuncio")
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    ok = announcement_service.delete_announcement(db, announcement_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    return success_response(data=None, message="Anuncio eliminado correctamente")


@router.post("/{announcement_id}/image", summary="Subir imagen de fondo del anuncio")
def upload_announcement_image(
    announcement_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    item = announcement_service.get_announcement(db, announcement_id)
    if not item:
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen válida")

    result = cloudinary_service.upload_announcement_image(file, announcement_id)
    updated = announcement_service.set_image(
        db, announcement_id, url=result["secure_url"], public_id=result.get("public_id")
    )
    return success_response(
        data=updated.model_dump() if updated else None,
        message="Imagen del anuncio subida correctamente",
    )
