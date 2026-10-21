"""
PROXVEL Backend - Destination Media Schemas.
"""
from pydantic import BaseModel

class DestinationMediaBase(BaseModel):
    id: int
    url: str | None = None
    public_id: str | None = None
    provider: str
    alt_text: str | None = None
    credit: str | None = None
    license_note: str | None = None
    position: int = 0
    is_active: bool = True
    media_type: str = "gallery"

    class Config:
        from_attributes = True

class DestinationMediaResponse(BaseModel):
    cover: DestinationMediaBase | None = None
    gallery: list[DestinationMediaBase] = []

class DestinationMediaAdminResponse(BaseModel):
    """Incluye items inactivos, para uso exclusivo en el panel admin."""
    cover: DestinationMediaBase | None = None
    inactive_covers: list[DestinationMediaBase] = []
    gallery: list[DestinationMediaBase] = []
    inactive_gallery: list[DestinationMediaBase] = []
