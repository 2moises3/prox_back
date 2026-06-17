"""
PROXVEL Backend - Destination Media Repository.
"""

from sqlalchemy.orm import Session
from app.models.destination_media_model import DestinationMedia

def get_media_for_destination(db: Session, destination_id: str) -> list[DestinationMedia]:
    return db.query(DestinationMedia).filter(
        DestinationMedia.destination_id == destination_id,
        DestinationMedia.is_active == True
    ).order_by(DestinationMedia.position).all()

def get_all_active_covers(db: Session) -> dict[str, str | None]:
    """
    Retorna un diccionario mapeando destination_id a cover_image_url
    para evitar consultas N+1 en listados.
    """
    covers = db.query(DestinationMedia).filter(
        DestinationMedia.media_type == "cover",
        DestinationMedia.is_active == True
    ).all()
    
    # Manejar múltiples covers si existen (tomar la primera)
    result = {}
    for c in covers:
        if c.destination_id not in result:
            result[c.destination_id] = c.url
    return result

def deactivate_covers(db: Session, destination_id: str) -> None:
    db.query(DestinationMedia).filter(
        DestinationMedia.destination_id == destination_id,
        DestinationMedia.media_type == "cover",
        DestinationMedia.is_active == True
    ).update({"is_active": False})
    db.commit()

def get_next_gallery_position(db: Session, destination_id: str) -> int:
    last_gallery = db.query(DestinationMedia).filter(
        DestinationMedia.destination_id == destination_id,
        DestinationMedia.media_type == "gallery"
    ).order_by(DestinationMedia.position.desc()).first()
    
    return last_gallery.position + 1 if last_gallery else 1

def create_media(db: Session, destination_id: str, media_type: str, url: str, public_id: str, provider: str, user_id: int | None = None, position: int = 0, alt_text: str | None = None, credit: str | None = None, license_note: str | None = None) -> DestinationMedia:
    new_media = DestinationMedia(
        destination_id=destination_id,
        media_type=media_type,
        provider=provider,
        public_id=public_id,
        url=url,
        position=position,
        alt_text=alt_text,
        credit=credit,
        license_note=license_note,
        is_active=True,
        uploaded_by_user_id=user_id
    )
    db.add(new_media)
    db.commit()
    db.refresh(new_media)
    return new_media

def update_media(db: Session, media_id: int, updates: dict) -> DestinationMedia | None:
    media = db.query(DestinationMedia).filter(DestinationMedia.id == media_id).first()
    if not media:
        return None
    for key, value in updates.items():
        setattr(media, key, value)
    db.commit()
    db.refresh(media)
    return media

def get_media_by_id(db: Session, media_id: int) -> DestinationMedia | None:
    return db.query(DestinationMedia).filter(DestinationMedia.id == media_id).first()

def get_all_media_for_destination(db: Session, destination_id: str) -> list[DestinationMedia]:
    """Retorna toda la multimedia (activa e inactiva) para uso admin."""
    return db.query(DestinationMedia).filter(
        DestinationMedia.destination_id == destination_id
    ).order_by(DestinationMedia.position).all()

def hard_delete_media(db: Session, media_id: int) -> bool:
    """Elimina físicamente el registro de la BD (Cloudinary se borra aparte)."""
    media = db.query(DestinationMedia).filter(DestinationMedia.id == media_id).first()
    if not media:
        return False
    db.delete(media)
    db.commit()
    return True
