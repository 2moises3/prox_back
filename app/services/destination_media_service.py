"""
PROXVEL Backend - Destination Media Service.
"""

from sqlalchemy.orm import Session
from app.repositories import destination_media_repository
from app.schemas.destination_media_schema import DestinationMediaResponse, DestinationMediaBase

def get_destination_media(db: Session, destination_id: str) -> DestinationMediaResponse:
    media_list = destination_media_repository.get_media_for_destination(db, destination_id)
    
    cover = None
    gallery = []
    
    for m in media_list:
        if m.media_type == "cover" and cover is None:
            cover = DestinationMediaBase.model_validate(m)
        elif m.media_type == "gallery":
            gallery.append(DestinationMediaBase.model_validate(m))
            
    return DestinationMediaResponse(cover=cover, gallery=gallery)

def get_covers_batch(db: Session) -> dict[str, str | None]:
    return destination_media_repository.get_all_active_covers(db)
