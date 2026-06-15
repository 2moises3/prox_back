"""
PROXVEL Backend - Favorite Repository.
Operaciones de base de datos para los favoritos.
"""

from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.favorite_model import Favorite
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.config.database import SessionLocal

class FavoriteRepository:
    """Repositorio para gestionar favoritos de usuarios."""
    
    def __init__(self, db_session: Session = None):
        self._db_session = db_session

    @property
    def db(self) -> Session:
        if self._db_session:
            return self._db_session
        self._db_session = SessionLocal()
        return self._db_session

    def get_user_favorites(self, user_id: str) -> List[Tuple[Favorite, Destination, TourismCatalog]]:
        """
        Obtiene los favoritos de un usuario, uniéndolos con el destino y su catálogo.
        Retorna una lista de tuplas (Favorite, Destination, TourismCatalog|None).
        """
        results = (
            self.db.query(Favorite, Destination, TourismCatalog)
            .join(Destination, Favorite.destination_id == Destination.destination_id)
            .outerjoin(TourismCatalog, Destination.destination_id == TourismCatalog.destination_id)
            .filter(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc())
            .all()
        )
        return results

    def add_favorite(self, user_id: str, destination_id: str) -> Tuple[Favorite | None, str | None]:
        """
        Agrega un destino a favoritos.
        Retorna (Favorite, None) si fue exitoso, o (None, mensaje_error).
        """
        # Verificar si el destino existe
        dest = self.db.query(Destination).filter(Destination.destination_id == destination_id).first()
        if not dest:
            return None, "El destino no existe."

        new_fav = Favorite(user_id=user_id, destination_id=destination_id)
        try:
            self.db.add(new_fav)
            self.db.commit()
            self.db.refresh(new_fav)
            return new_fav, None
        except IntegrityError:
            self.db.rollback()
            return None, "El destino ya está en favoritos."

    def remove_favorite(self, user_id: str, destination_id: str) -> bool:
        """
        Elimina un favorito.
        Retorna True si fue eliminado, False si no existía.
        """
        fav = self.db.query(Favorite).filter(
            Favorite.user_id == user_id, 
            Favorite.destination_id == destination_id
        ).first()
        
        if fav:
            self.db.delete(fav)
            self.db.commit()
            return True
        return False

    def check_favorite(self, user_id: str, destination_id: str) -> bool:
        """Verifica si un destino es favorito del usuario."""
        fav = self.db.query(Favorite).filter(
            Favorite.user_id == user_id, 
            Favorite.destination_id == destination_id
        ).first()
        return fav is not None

# Instancia global por defecto
db_favorite_repository = FavoriteRepository()
