"""
PROXVEL Backend - Destination Media Routes.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.services import destination_media_service

router = APIRouter(prefix="/destinations", tags=["Multimedia"])

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
