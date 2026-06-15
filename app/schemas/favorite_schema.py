"""
PROXVEL Backend - Favorite Schemas.
Schemas Pydantic para endpoints de favoritos.
"""

from pydantic import BaseModel
from datetime import datetime


class FavoriteItemResponse(BaseModel):
    """Respuesta detallada de un destino favorito."""
    destination_id: str
    name: str
    city: str | None = None
    region: str | None = None
    category: str | None = None
    cover_image_url: str | None = None
    rating: float | None = None
    is_favorite: bool = True
    created_at: datetime | None = None


class FavoriteToggleResponse(BaseModel):
    """Respuesta para agregar/eliminar favorito."""
    destination_id: str
    is_favorite: bool
