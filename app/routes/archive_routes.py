"""
PROXVEL Backend - Archive Routes.
Endpoints para gestión de destinos archivados.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.core.security import get_current_user
from app.schemas.user_schema import UserResponse
from app.schemas.archive_schema import ArchiveItemResponse, ArchiveToggleResponse
from app.services.archive_service import archive_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/archives", tags=["Archives"])

@router.get(
    "",
    summary="Listar archivados",
    description="Devuelve todos los destinos archivados del usuario autenticado.",
    response_model=dict
)
def get_archives(current_user: UserResponse = Depends(get_current_user)):
    archives = archive_service.get_user_archives(current_user.user_id)
    return success_response(
        data=[arc.model_dump() for arc in archives],
        message="Archivados obtenidos correctamente"
    )

@router.post(
    "/{destination_id}",
    summary="Agregar archivo",
    description="Agrega un destino a la lista de archivados del usuario.",
    response_model=dict
)
def add_archive(destination_id: str, current_user: UserResponse = Depends(get_current_user)):
    result, error = archive_service.add_archive(current_user.user_id, destination_id)
    if error:
        if "ya está" in error:
            return success_response(
                data={"destination_id": destination_id, "is_archived": True},
                message=error
            )
        raise HTTPException(status_code=404, detail=error)
        
    return success_response(
        data=result.model_dump(),
        message="Destino archivado"
    )

@router.delete(
    "/{destination_id}",
    summary="Eliminar archivo",
    description="Elimina un destino de la lista de archivados (desarchivar).",
    response_model=dict
)
def remove_archive(destination_id: str, current_user: UserResponse = Depends(get_current_user)):
    result, error = archive_service.remove_archive(current_user.user_id, destination_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
        
    return success_response(
        data=result.model_dump(),
        message="Destino desarchivado"
    )

@router.get(
    "/check/{destination_id}",
    summary="Verificar si está archivado",
    description="Verifica si un destino específico está archivado.",
    response_model=dict
)
def check_archive(destination_id: str, current_user: UserResponse = Depends(get_current_user)):
    is_arc = archive_service.check_archive(current_user.user_id, destination_id)
    return success_response(
        data={"destination_id": destination_id, "is_archived": is_arc},
        message="Verificación de archivo completada"
    )
