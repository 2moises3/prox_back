"""
PROXVEL Backend - Favorite Service.
Lógica de negocio para favoritos.
"""

from typing import List, Tuple
from app.repositories.favorite_repository import db_favorite_repository
from app.schemas.favorite_schema import FavoriteItemResponse, FavoriteToggleResponse

class FavoriteService:
    
    def get_user_favorites(self, user_id: str) -> List[FavoriteItemResponse]:
        results = db_favorite_repository.get_user_favorites(user_id)
        
        from app.services import destination_media_service
        active_covers = destination_media_service.get_covers_batch(db_favorite_repository.db)

        response_list = []
        for fav, dest, catalog in results:
            item = FavoriteItemResponse(
                destination_id=fav.destination_id,
                name=dest.destination,
                city=catalog.city if catalog else None,
                region=catalog.region if catalog else None,
                category=catalog.category if catalog else None,
                cover_image_url=active_covers.get(fav.destination_id),
                rating=None, # No hay una valoración agregada verificada en este contrato.
                is_favorite=True,
                created_at=fav.created_at
            )
            response_list.append(item)
            
        return response_list

    def add_favorite(self, user_id: str, destination_id: str) -> Tuple[FavoriteToggleResponse | None, str | None]:
        fav, error = db_favorite_repository.add_favorite(user_id, destination_id)
        if error:
            return None, error
            
        return FavoriteToggleResponse(destination_id=destination_id, is_favorite=True), None

    def remove_favorite(self, user_id: str, destination_id: str) -> Tuple[FavoriteToggleResponse | None, str | None]:
        success = db_favorite_repository.remove_favorite(user_id, destination_id)
        if not success:
            # Idempotente: si no estaba en favoritos, devolvemos success igualmente
            # O devolvemos error si se prefiere. Se opta por 200 idempotente.
            pass
            
        return FavoriteToggleResponse(destination_id=destination_id, is_favorite=False), None

    def check_favorite(self, user_id: str, destination_id: str) -> bool:
        return db_favorite_repository.check_favorite(user_id, destination_id)

favorite_service = FavoriteService()
