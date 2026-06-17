"""
PROXVEL Backend - Admin Release Routes (6B).
Gestión de versiones de la APK.
- Subir / publicar / eliminar: solo super_admin.
- Listar: admin o super_admin.
El binario se sube a Cloudinary (raw) o se referencia por apk_url externa.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form

from app.core.security import require_admin_or_super_admin, require_super_admin
from app.schemas.user_schema import UserResponse
from app.schemas.release_schema import ReleaseUpdate, ReleasePublishUpdate
from app.services import release_service, cloudinary_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/admin/releases", tags=["Admin - Releases"])


@router.get("", summary="Listar versiones de la APK")
def list_releases(
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    releases = release_service.list_releases()
    return success_response(
        data=[r.model_dump() for r in releases],
        message="Versiones obtenidas correctamente",
    )


@router.post("", summary="Registrar una nueva versión (sube APK o usa apk_url)", status_code=201)
def create_release(
    version_name: str = Form(...),
    version_code: int = Form(...),
    platform: str = Form("android"),
    changelog: Optional[str] = Form(None),
    apk_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: UserResponse = Depends(require_super_admin),
):
    data = {
        "version_name": version_name,
        "version_code": version_code,
        "platform": platform,
        "changelog": changelog,
        "apk_url": apk_url,
        "file_public_id": None,
        "file_size": None,
        "created_by": current_user.user_id,
    }

    # Si se sube un archivo, debe ser .apk y se almacena en Cloudinary (raw).
    if file is not None and file.filename:
        if not file.filename.lower().endswith(".apk"):
            raise HTTPException(status_code=400, detail="El archivo debe ser una APK (.apk).")
        uploaded = cloudinary_service.upload_release_apk(file, version_name)
        data["apk_url"] = uploaded["secure_url"]
        data["file_public_id"] = uploaded["public_id"]
        data["file_size"] = uploaded.get("bytes")

    created, error = release_service.create_release(data)
    if error:
        raise HTTPException(status_code=422, detail=error)
    return success_response(data=created.model_dump(), message="Versión registrada correctamente")


@router.patch("/{release_id}", summary="Actualizar metadata de una versión")
def update_release(
    release_id: int,
    payload: ReleaseUpdate,
    current_user: UserResponse = Depends(require_super_admin),
):
    updated = release_service.update_release(release_id, payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Versión no encontrada")
    return success_response(data=updated.model_dump(), message="Versión actualizada correctamente")


@router.patch("/{release_id}/publish", summary="Publicar o despublicar una versión")
def publish_release(
    release_id: int,
    payload: ReleasePublishUpdate,
    current_user: UserResponse = Depends(require_super_admin),
):
    updated = release_service.set_published(release_id, payload.is_published)
    if not updated:
        raise HTTPException(status_code=404, detail="Versión no encontrada")
    estado = "publicada" if payload.is_published else "despublicada"
    return success_response(data=updated.model_dump(), message=f"Versión {estado} correctamente")


@router.delete("/{release_id}", summary="Eliminar una versión")
def delete_release(
    release_id: int,
    current_user: UserResponse = Depends(require_super_admin),
):
    deleted = release_service.delete_release(release_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Versión no encontrada")
    return success_response(data=None, message="Versión eliminada correctamente")
