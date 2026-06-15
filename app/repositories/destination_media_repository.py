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
