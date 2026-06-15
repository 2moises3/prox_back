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
    position: int = 0

    class Config:
        from_attributes = True

class DestinationMediaResponse(BaseModel):
    cover: DestinationMediaBase | None = None
    gallery: list[DestinationMediaBase] = []
