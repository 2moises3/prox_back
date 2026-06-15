"""
PROXVEL Backend - Destination Media Routes.
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.config.database import get_db
from app.config.settings import get_settings
from app.services import destination_media_service
from app.schemas.media_upload_schema import MediaUploadResponse, MediaPatchRequest
from app.core.security import require_admin_or_super_admin
from app.schemas.user_schema import UserResponse

router = APIRouter(prefix="/destinations", tags=["Multimedia"])
settings = get_settings()

@router.get("/{destination_id}/media")
def get_media(destination_id: str, db: Session = Depends(get_db)):
    """
    Obtiene la multimedia limpia del destino.
    Si no hay, devuelve null y arreglos vacíos.
    """
    media = destination_media_service.get_destination_media(db, destination_id)
    return {
        "success": True,
        "message": "Multimedia del destino obtenida correctamente",
        "data": media.model_dump()
    }

@router.post("/{destination_id}/media/upload", response_model=MediaUploadResponse)
def upload_media(
    destination_id: str,
    file: UploadFile = File(...),
    media_type: str = Form(...),
    position: Optional[int] = Form(None),
    alt_text: Optional[str] = Form(None),
    credit: Optional[str] = Form(None),
    license_note: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin)
):
    """Sube una nueva imagen a Cloudinary y la registra en PostgreSQL."""
    if media_type not in ["cover", "gallery"]:
        raise HTTPException(status_code=400, detail="media_type debe ser 'cover' o 'gallery'")
        
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo debe ser una imagen válida")
        
    try:
        new_media = destination_media_service.upload_media(
            db=db,
            file=file,
            destination_id=destination_id,
            media_type=media_type,
            user_id=None,
            position=position,
            alt_text=alt_text,
            credit=credit,
            license_note=license_note
        )
        return MediaUploadResponse(
            success=True,
            message="Imagen subida y guardada exitosamente",
            media=new_media.model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{destination_id}/media/{media_id}", response_model=MediaUploadResponse)
def patch_media(
    destination_id: str,
    media_id: int,
    request: MediaPatchRequest,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin)
):
    """Actualiza la metadata de una imagen (ej. posición, is_active)."""
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")
        
    updated_media = destination_media_service.update_media(db, media_id, updates)
    if not updated_media:
        raise HTTPException(status_code=404, detail="Media no encontrada")
        
    return MediaUploadResponse(
        success=True,
        message="Media actualizada correctamente",
        media=updated_media.model_dump()
    )

@router.delete("/{destination_id}/media/{media_id}")
def delete_media(
    destination_id: str,
    media_id: int,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin)
):
    """Aplica soft-delete (is_active=False) a una imagen."""
    success = destination_media_service.delete_media(db, media_id)
    if not success:
        raise HTTPException(status_code=404, detail="Media no encontrada")
        
    return {
        "success": True,
        "message": "Media eliminada (soft delete) exitosamente"
    }
