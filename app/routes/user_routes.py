"""
PROXVEL Backend - User Routes.
"""
import logging

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File
from typing import List

from app.services import user_service
from app.schemas.user_schema import UserResponse, UserCreate, UserUpdate
from app.utils.response_builder import success_response
from app.core.security import get_current_user
from app.core.rate_limit import enforce_register_allowed
from app.config.settings import get_settings

logger = logging.getLogger(__name__)

from pydantic import BaseModel, Field
from datetime import datetime
from app.core.legal import TERMS_VERSION
from app.core.rate_limit import client_ip
from app.repositories import db_user_repository
from app.services import user_admin_service
from app.utils.hash_util import verify_password

router = APIRouter(prefix="/users", tags=["Users"])
audit_logger = logging.getLogger("proxvel.audit")

@router.post("", response_model=dict, summary="Crear nuevo usuario", status_code=201)
def create_user(user: UserCreate, _: None = Depends(enforce_register_allowed)):
    # Registro público: se limita por IP (dependencia) para frenar la creación masiva de cuentas.
    if not user.accepted_terms:
        raise HTTPException(
            status_code=422,
            detail="Debes aceptar los Términos y la Política de Privacidad y confirmar que eres mayor de 18 años.",
        )
    created_user, error = user_service.create_user(user)
    if error:
        raise HTTPException(status_code=409, detail=error)
    return success_response(data=created_user.model_dump(), message="Usuario creado correctamente")

@router.get("/{user_id}", response_model=dict, summary="Obtener usuario por ID")
def get_user_by_id(user_id: str, current_user: UserResponse = Depends(get_current_user)):
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para acceder a este usuario")
        
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return success_response(data=user.model_dump(), message="Usuario obtenido")

@router.patch("/{user_id}", response_model=dict, summary="Actualizar usuario")
def update_user(user_id: str, user_update: UserUpdate, current_user: UserResponse = Depends(get_current_user)):
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar a este usuario")
        
    updated_user, error = user_service.update_user(user_id, user_update)
    if error:
        if "no encontrado" in error:
            raise HTTPException(status_code=404, detail=error)
        raise HTTPException(status_code=409, detail=error)
    return success_response(data=updated_user.model_dump(), message="Usuario actualizado")

from app.services.cloudinary_service import upload_avatar_image

_AVATAR_SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}


def _is_valid_avatar(content: bytes, content_type: str | None) -> bool:
    """Tipo permitido y firma real del archivo (no basta con el Content-Type del cliente)."""
    sigs = _AVATAR_SIGNATURES.get((content_type or "").lower())
    if not sigs or not any(content.startswith(sig) for sig in sigs):
        return False
    return content_type.lower() != "image/webp" or content[8:12] == b"WEBP"


@router.post("/{user_id}/avatar", response_model=dict, summary="Subir imagen de perfil")
async def upload_user_avatar(
    user_id: str,
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user)
):
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar este avatar")

    # Verificar que el usuario existe antes de subir a Cloudinary
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    max_bytes = get_settings().MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"La imagen supera el máximo de {get_settings().MAX_UPLOAD_SIZE_MB} MB")
    if not _is_valid_avatar(content, file.content_type):
        raise HTTPException(status_code=400, detail="Formato de imagen no válido. Usa JPG, PNG o WEBP.")

    try:
        result = upload_avatar_image(content, "proxvel/users/avatars")
        secure_url = result.get("secure_url")
        if not secure_url:
            raise ValueError("Cloudinary no devolvió la URL")

        updated_user, error = user_service.update_user(user_id, UserUpdate(avatar_url=secure_url))
    except Exception:
        logger.exception("Error subiendo avatar de %s", user_id)
        raise HTTPException(status_code=500, detail="No pudimos procesar la imagen. Intenta nuevamente.")

    if error:
        raise HTTPException(status_code=400, detail=error)

    return success_response(
        data={"avatar_url": secure_url},
        message="Imagen de perfil actualizada correctamente"
    )

from app.services import traveler_profile_service
from app.schemas.traveler_profile_schema import TravelerProfileUpdate

@router.get("/{user_id}/traveler-profile", response_model=dict, summary="Obtener perfil viajero")
def get_traveler_profile(user_id: str, current_user: UserResponse = Depends(get_current_user)):
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para acceder a este perfil")
        
    profile, error = traveler_profile_service.get_profile_by_user_id(user_id)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return success_response(data=profile.model_dump(), message="Perfil viajero obtenido")

@router.put("/{user_id}/traveler-profile", response_model=dict, summary="Crear o reemplazar perfil viajero")
def put_traveler_profile(user_id: str, profile_update: TravelerProfileUpdate, current_user: UserResponse = Depends(get_current_user)):
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar este perfil")
        
    profile, error = traveler_profile_service.update_profile(user_id, profile_update, is_partial=False)
    if error:
        if "no encontrado" in error:
            raise HTTPException(status_code=404, detail=error)
        raise HTTPException(status_code=400, detail=error)
    return success_response(data=profile.model_dump(), message="Perfil viajero guardado correctamente")

@router.patch("/{user_id}/traveler-profile", response_model=dict, summary="Actualizar parcialmente perfil viajero")
def patch_traveler_profile(user_id: str, profile_update: TravelerProfileUpdate, current_user: UserResponse = Depends(get_current_user)):
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para modificar este perfil")
        
    profile, error = traveler_profile_service.update_profile(user_id, profile_update, is_partial=True)
    if error:
        if "no encontrado" in error or "no existe" in error:
            raise HTTPException(status_code=404, detail=error)
        raise HTTPException(status_code=400, detail=error)
    return success_response(data=profile.model_dump(), message="Perfil viajero actualizado correctamente")


# ── Consentimiento, eliminación de cuenta (derechos del usuario) ─────────────

class DeleteAccountRequest(BaseModel):
    password: str = Field(..., min_length=1)


@router.post("/me/accept-terms", response_model=dict, summary="Aceptar la versión vigente de Términos y Privacidad")
def accept_terms(request: Request, current_user: UserResponse = Depends(get_current_user)):
    updated = db_user_repository.update_user(current_user.user_id, {
        "accepted_terms_version": TERMS_VERSION,
        "accepted_terms_at": datetime.utcnow(),
    })
    if not updated:
        raise HTTPException(status_code=500, detail="No pudimos registrar tu aceptación. Intenta de nuevo.")
    audit_logger.info("AUDIT terms_accepted user=%s ip=%s version=%s", current_user.user_id, client_ip(request), TERMS_VERSION)
    return success_response(data=UserResponse.model_validate(updated).model_dump(), message="Aceptación registrada")


@router.post("/me/delete-account", response_model=dict, summary="Eliminar mi cuenta (14 días de gracia)")
def delete_my_account(payload: DeleteAccountRequest, request: Request,
                      current_user: UserResponse = Depends(get_current_user)):
    ip = client_ip(request)
    user = db_user_repository.get_user_by_id(current_user.user_id)
    if not user or not verify_password(payload.password, user.password_hash):
        audit_logger.warning("AUDIT account_delete DENIED user=%s ip=%s reason=wrong_password", current_user.user_id, ip)
        raise HTTPException(status_code=403, detail="La contraseña no es correcta.")
    result, error, code = user_admin_service.request_own_deletion(current_user.user_id)
    if error:
        raise HTTPException(status_code=code or 400, detail=error)
    audit_logger.info("AUDIT account_delete REQUESTED user=%s ip=%s", current_user.user_id, ip)
    days = get_settings().ACCOUNT_DELETION_GRACE_DAYS
    return success_response(
        data={"grace_days": days},
        message=f"Tu cuenta se eliminará en {days} días. Si cambias de opinión, escríbenos antes a soporte@m3biznovatech.com.",
    )


@router.get("/me/deletion-policy", response_model=dict, summary="Plazo configurado para eliminar mi cuenta")
def get_deletion_policy(_: UserResponse = Depends(get_current_user)):
    return success_response(data={"grace_days": get_settings().ACCOUNT_DELETION_GRACE_DAYS})
