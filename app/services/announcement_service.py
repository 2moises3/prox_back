"""
PROXVEL Backend - Announcement Service.
Lógica de negocio de anuncios internos.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.announcement_model import Announcement
from app.repositories import announcement_repository
from app.schemas.announcement_schema import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
    AnnouncementPublic,
)


def compute_status(obj: Announcement) -> str:
    """Estado derivado: active | scheduled | expired | inactive."""
    if not obj.is_active:
        return "inactive"

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if obj.starts_at and obj.starts_at > now:
        return "scheduled"
    if obj.ends_at and obj.ends_at < now:
        return "expired"
    return "active"


def _to_response(obj: Announcement) -> AnnouncementResponse:
    resp = AnnouncementResponse.model_validate(obj)
    resp.status = compute_status(obj)
    return resp


def list_announcements(db: Session) -> list[AnnouncementResponse]:
    return [_to_response(o) for o in announcement_repository.list_announcements(db)]


def get_announcement(db: Session, announcement_id: int) -> AnnouncementResponse | None:
    obj = announcement_repository.get_by_id(db, announcement_id)
    return _to_response(obj) if obj else None


def create_announcement(
    db: Session, payload: AnnouncementCreate, created_by: str | None
) -> AnnouncementResponse:
    data = payload.model_dump()
    data["created_by"] = created_by
    obj = announcement_repository.create(db, data)
    return _to_response(obj)


def update_announcement(
    db: Session, announcement_id: int, payload: AnnouncementUpdate
) -> AnnouncementResponse | None:
    obj = announcement_repository.get_by_id(db, announcement_id)
    if not obj:
        return None

    updates = payload.model_dump(exclude_unset=True)

    # Validación cruzada de fechas con valores finales (actuales + entrantes)
    final_start = updates.get("starts_at", obj.starts_at)
    final_end = updates.get("ends_at", obj.ends_at)
    if final_start and final_end and final_end <= final_start:
        raise ValueError("ends_at debe ser posterior a starts_at")

    obj = announcement_repository.update(db, obj, updates)
    return _to_response(obj)


def set_image(
    db: Session, announcement_id: int, url: str, public_id: str | None
) -> AnnouncementResponse | None:
    obj = announcement_repository.get_by_id(db, announcement_id)
    if not obj:
        return None
    obj = announcement_repository.update(
        db, obj, {"background_image_url": url, "media_public_id": public_id}
    )
    return _to_response(obj)


def delete_announcement(db: Session, announcement_id: int) -> bool:
    obj = announcement_repository.get_by_id(db, announcement_id)
    if not obj:
        return False
    announcement_repository.delete(db, obj)
    return True


def list_public_active(
    db: Session, placement: str | None = None
) -> list[AnnouncementPublic]:
    rows = announcement_repository.list_public_active(db, placement=placement)
    return [AnnouncementPublic.model_validate(o) for o in rows]
