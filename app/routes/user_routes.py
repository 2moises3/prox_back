"""
PROXVEL Backend - User Routes.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List

from app.services import user_service
from app.schemas.user_schema import UserResponse, UserCreate, UserUpdate
from app.utils.response_builder import success_response
from app.core.security import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("", response_model=dict, summary="Crear nuevo usuario", status_code=201)
def create_user(user: UserCreate):
    created_user, error = user_service.create_user(user)
    if error:
        raise HTTPException(status_code=409, detail=error)
    return success_response(data=created_user.model_dump(), message="Usuario creado correctamente")

@router.get("/demo", response_model=dict, summary="Obtener usuarios demo")
def get_demo_users():
    users = user_service.get_demo_users()
    return success_response(data=[u.model_dump() for u in users], message="Usuarios demo obtenidos")

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
        
    try:
        # Leer el contenido del archivo
        content = await file.read()
        
        # Subir a Cloudinary en un folder específico
        folder_path = "proxvel/users/avatars"
        result = upload_avatar_image(content, folder_path)
        secure_url = result.get("secure_url")
        
        if not secure_url:
            raise HTTPException(status_code=500, detail="Error al obtener la URL de Cloudinary")
            
        # Actualizar el avatar_url del usuario
        update_data = UserUpdate(avatar_url=secure_url)
        updated_user, error = user_service.update_user(user_id, update_data)
        
        if error:
            raise HTTPException(status_code=400, detail=error)
            
        return success_response(
            data={"avatar_url": secure_url}, 
            message="Imagen de perfil actualizada correctamente"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la imagen: {str(e)}")

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
