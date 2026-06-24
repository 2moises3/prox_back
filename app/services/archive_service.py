"""
PROXVEL Backend - Archive Service.
Lógica de negocio para archivos.
"""

from typing import List, Tuple
from app.repositories.archive_repository import db_archive_repository
from app.schemas.archive_schema import ArchiveItemResponse, ArchiveToggleResponse

class ArchiveService:
    
    def get_user_archives(self, user_id: str) -> List[ArchiveItemResponse]:
        results = db_archive_repository.get_user_archives(user_id)
        
        from app.services import destination_media_service
        active_covers = destination_media_service.get_covers_batch(db_archive_repository.db)

        response_list = []
        for arc, dest, catalog in results:
            item = ArchiveItemResponse(
                destination_id=arc.destination_id,
                name=dest.destination,
                city=catalog.city if catalog else None,
                region=catalog.region if catalog else None,
                category=catalog.category if catalog else None,
                cover_image_url=active_covers.get(arc.destination_id),
                is_archived=True,
                created_at=arc.created_at
            )
            response_list.append(item)
            
        return response_list

    def add_archive(self, user_id: str, destination_id: str) -> Tuple[ArchiveToggleResponse | None, str | None]:
        arc, error = db_archive_repository.add_archive(user_id, destination_id)
        if error:
            return None, error
            
        return ArchiveToggleResponse(destination_id=destination_id, is_archived=True), None

    def remove_archive(self, user_id: str, destination_id: str) -> Tuple[ArchiveToggleResponse | None, str | None]:
        success = db_archive_repository.remove_archive(user_id, destination_id)
        if not success:
            pass
            
        return ArchiveToggleResponse(destination_id=destination_id, is_archived=False), None

    def check_archive(self, user_id: str, destination_id: str) -> bool:
        return db_archive_repository.check_archive(user_id, destination_id)

archive_service = ArchiveService()
