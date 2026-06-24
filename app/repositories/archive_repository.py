"""
PROXVEL Backend - Archive Repository.
Operaciones de base de datos para los archivos.
"""

from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.archive_model import Archive
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.config.database import SessionLocal

class ArchiveRepository:
    """Repositorio para gestionar destinos archivados de usuarios."""
    
    def __init__(self, db_session: Session = None):
        self._db_session = db_session

    @property
    def db(self) -> Session:
        if self._db_session:
            return self._db_session
        self._db_session = SessionLocal()
        return self._db_session

    def get_user_archives(self, user_id: str) -> List[Tuple[Archive, Destination, TourismCatalog]]:
        """
        Obtiene los archivos de un usuario.
        """
        results = (
            self.db.query(Archive, Destination, TourismCatalog)
            .join(Destination, Archive.destination_id == Destination.destination_id)
            .outerjoin(TourismCatalog, Destination.destination_id == TourismCatalog.destination_id)
            .filter(Archive.user_id == user_id)
            .order_by(Archive.created_at.desc())
            .all()
        )
        return results

    def add_archive(self, user_id: str, destination_id: str) -> Tuple[Archive | None, str | None]:
        """
        Archiva un destino.
        """
        dest = self.db.query(Destination).filter(Destination.destination_id == destination_id).first()
        if not dest:
            return None, "El destino no existe."

        new_arc = Archive(user_id=user_id, destination_id=destination_id)
        try:
            self.db.add(new_arc)
            self.db.commit()
            self.db.refresh(new_arc)
            return new_arc, None
        except IntegrityError:
            self.db.rollback()
            return None, "El destino ya está archivado."

    def remove_archive(self, user_id: str, destination_id: str) -> bool:
        """
        Desarchiva un destino.
        """
        arc = self.db.query(Archive).filter(
            Archive.user_id == user_id, 
            Archive.destination_id == destination_id
        ).first()
        
        if arc:
            self.db.delete(arc)
            self.db.commit()
            return True
        return False

    def check_archive(self, user_id: str, destination_id: str) -> bool:
        """Verifica si un destino está archivado."""
        arc = self.db.query(Archive).filter(
            Archive.user_id == user_id, 
            Archive.destination_id == destination_id
        ).first()
        return arc is not None

db_archive_repository = ArchiveRepository()
