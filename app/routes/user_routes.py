"""
PROXVEL Backend - User Routes.
"""
from fastapi import APIRouter, HTTPException
from typing import List

from app.services import user_service
from app.schemas.user_schema import UserResponse
from app.utils.response_builder import success_response

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/demo", response_model=dict, summary="Obtener usuarios demo")
def get_demo_users():
    users = user_service.get_demo_users()
    return success_response(data=[u.model_dump() for u in users], message="Usuarios demo obtenidos")

@router.get("/{user_id}", response_model=dict, summary="Obtener usuario por ID")
def get_user_by_id(user_id: str):
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return success_response(data=user.model_dump(), message="Usuario obtenido")
