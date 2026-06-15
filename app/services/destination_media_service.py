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

def upload_media(db: Session, file, destination_id: str, media_type: str, user_id: int | None = None, position: int | None = None, alt_text: str | None = None, credit: str | None = None, license_note: str | None = None) -> DestinationMediaBase:
    from app.services import cloudinary_service
    
    # 1. Subir a Cloudinary
    upload_result = cloudinary_service.upload_destination_image(file, destination_id, media_type)
    
    # 2. Desactivar portadas si es cover
    if media_type == "cover":
        destination_media_repository.deactivate_covers(db, destination_id)
        final_position = 0
    else:
        # Gallery
        if position is None:
            final_position = destination_media_repository.get_next_gallery_position(db, destination_id)
        else:
            final_position = position

    # 3. Crear en BD
    new_media = destination_media_repository.create_media(
        db=db,
        destination_id=destination_id,
        media_type=media_type,
        url=upload_result["secure_url"],
        public_id=upload_result["public_id"],
        provider="cloudinary",
        user_id=user_id,
        position=final_position,
        alt_text=alt_text,
        credit=credit,
        license_note=license_note
    )
    
    return DestinationMediaBase.model_validate(new_media)

def update_media(db: Session, media_id: int, updates: dict) -> DestinationMediaBase | None:
    # Check current media
    media = destination_media_repository.get_media_by_id(db, media_id)
    if not media:
        return None
        
    # If activating a cover, deactivate previous covers
    if updates.get("is_active") is True and media.media_type == "cover":
        destination_media_repository.deactivate_covers(db, media.destination_id)
        
    updated = destination_media_repository.update_media(db, media_id, updates)
    return DestinationMediaBase.model_validate(updated) if updated else None

def delete_media(db: Session, media_id: int) -> bool:
    # Soft delete
    updated = destination_media_repository.update_media(db, media_id, {"is_active": False})
    return updated is not None
