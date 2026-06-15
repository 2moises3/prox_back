"""
PROXVEL Backend - Favorite Routes.
Endpoints para gestión de destinos favoritos.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.core.security import get_current_user
from app.schemas.user_schema import UserResponse
from app.schemas.favorite_schema import FavoriteItemResponse, FavoriteToggleResponse
from app.services.favorite_service import favorite_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/favorites", tags=["Favorites"])

@router.get(
    "",
    summary="Listar favoritos",
    description="Devuelve todos los destinos favoritos del usuario autenticado.",
    response_model=dict
)
def get_favorites(current_user: UserResponse = Depends(get_current_user)):
    favorites = favorite_service.get_user_favorites(current_user.user_id)
    return success_response(
        data=[fav.model_dump() for fav in favorites],
        message="Favoritos obtenidos correctamente"
    )

@router.post(
    "/{destination_id}",
    summary="Agregar favorito",
    description="Agrega un destino a la lista de favoritos del usuario.",
    response_model=dict
)
def add_favorite(destination_id: str, current_user: UserResponse = Depends(get_current_user)):
    result, error = favorite_service.add_favorite(current_user.user_id, destination_id)
    if error:
        if "ya está" in error:
            # Según la regla, preferir 200 con mensaje
            return success_response(
                data={"destination_id": destination_id, "is_favorite": True},
                message=error
            )
        # 404 si el destino no existe
        raise HTTPException(status_code=404, detail=error)
        
    return success_response(
        data=result.model_dump(),
        message="Destino agregado a favoritos"
    )

@router.delete(
    "/{destination_id}",
    summary="Eliminar favorito",
    description="Elimina un destino de la lista de favoritos del usuario.",
    response_model=dict
)
def remove_favorite(destination_id: str, current_user: UserResponse = Depends(get_current_user)):
    result, error = favorite_service.remove_favorite(current_user.user_id, destination_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
        
    return success_response(
        data=result.model_dump(),
        message="Destino eliminado de favoritos"
    )

@router.get(
    "/check/{destination_id}",
    summary="Verificar si es favorito",
    description="Verifica si un destino específico es favorito del usuario.",
    response_model=dict
)
def check_favorite(destination_id: str, current_user: UserResponse = Depends(get_current_user)):
    is_fav = favorite_service.check_favorite(current_user.user_id, destination_id)
    return success_response(
        data={"destination_id": destination_id, "is_favorite": is_fav},
        message="Verificación de favorito completada"
    )
