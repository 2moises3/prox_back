"""
PROXVEL Backend - Archive Schemas.
Schemas Pydantic para endpoints de archivados.
"""

from pydantic import BaseModel
from datetime import datetime


class ArchiveItemResponse(BaseModel):
    """Respuesta detallada de un destino archivado."""
    destination_id: str
    name: str
    city: str | None = None
    region: str | None = None
    category: str | None = None
    cover_image_url: str | None = None
    is_archived: bool = True
    created_at: datetime | None = None


class ArchiveToggleResponse(BaseModel):
    """Respuesta para agregar/eliminar archivado."""
    destination_id: str
    is_archived: bool
