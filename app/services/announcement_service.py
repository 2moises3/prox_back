"""
PROXVEL Backend - Announcement Service.
Lógica de negocio de anuncios internos.
"""

from datetime import datetime, timezone

from sqlalchemy import update as sql_update
from sqlalchemy.orm import Session

from app.models.announcement_model import Announcement
from app.models.destination_model import Destination
from app.repositories import announcement_repository
from app.schemas.announcement_schema import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AnnouncementResponse,
    AnnouncementPublic,
)

# Columna de métrica que suma cada evento reportado por la app.
_EVENT_COLUMNS = {"impression": "impressions", "click": "clicks", "dismiss": "dismissals"}


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


def _to_response(db: Session, obj: Announcement) -> AnnouncementResponse:
    resp = AnnouncementResponse.model_validate(obj)
    resp.status = compute_status(obj)
    if obj.target_destination_id:
        dest = _find_destination(db, obj.target_destination_id)
        resp.target_destination_name = dest.destination if dest else None
    return resp


def _find_destination(db: Session, destination_id: str) -> Destination | None:
    return db.query(Destination).filter(Destination.destination_id == destination_id).first()


def _check_target(db: Session, destination_id: str | None) -> None:
    if destination_id and _find_destination(db, destination_id) is None:
        raise ValueError(f"El destino '{destination_id}' no existe.")


def _check_cta_destination(db: Session, cta_url: str | None) -> None:
    if cta_url and cta_url.startswith("/destination/"):
        _check_target(db, cta_url.rsplit("/", 1)[-1])


def list_announcements(db: Session) -> list[AnnouncementResponse]:
    return [_to_response(db, o) for o in announcement_repository.list_announcements(db)]


def get_announcement(db: Session, announcement_id: int) -> AnnouncementResponse | None:
    obj = announcement_repository.get_by_id(db, announcement_id)
    return _to_response(db, obj) if obj else None


def create_announcement(
    db: Session, payload: AnnouncementCreate, created_by: str | None
) -> AnnouncementResponse:
    _check_target(db, payload.target_destination_id)
    _check_cta_destination(db, payload.cta_url)
    data = payload.model_dump()
    data["created_by"] = created_by
    obj = announcement_repository.create(db, data)
    return _to_response(db, obj)


def update_announcement(
    db: Session, announcement_id: int, payload: AnnouncementUpdate
) -> AnnouncementResponse | None:
    obj = announcement_repository.get_by_id(db, announcement_id)
    if not obj:
        return None

    updates = payload.model_dump(exclude_unset=True)

    # Validación cruzada con los valores finales (actuales + entrantes)
    final = lambda key: updates.get(key, getattr(obj, key))  # noqa: E731
    if final("starts_at") and final("ends_at") and final("ends_at") <= final("starts_at"):
        raise ValueError("ends_at debe ser posterior a starts_at")
    if bool(final("cta_text")) != bool(final("cta_url")):
        raise ValueError("El botón necesita texto y acción (o deja ambos vacíos).")
    if final("placement") != "destination_detail":
        updates["target_destination_id"] = None
    _check_target(db, updates.get("target_destination_id"))
    _check_cta_destination(db, updates.get("cta_url"))

    obj = announcement_repository.update(db, obj, updates)
    return _to_response(db, obj)


def set_image(
    db: Session, announcement_id: int, url: str, public_id: str | None
) -> AnnouncementResponse | None:
    obj = announcement_repository.get_by_id(db, announcement_id)
    if not obj:
        return None
    obj = announcement_repository.update(
        db, obj, {"background_image_url": url, "media_public_id": public_id}
    )
    return _to_response(db, obj)


def remove_image(db: Session, announcement_id: int) -> AnnouncementResponse | None:
    obj = announcement_repository.get_by_id(db, announcement_id)
    if not obj:
        return None
    obj = announcement_repository.update(db, obj, {"background_image_url": None, "media_public_id": None})
    return _to_response(db, obj)


def delete_announcement(db: Session, announcement_id: int) -> bool:
    obj = announcement_repository.get_by_id(db, announcement_id)
    if not obj:
        return False
    announcement_repository.delete(db, obj)
    return True


def list_public_active(
    db: Session, placement: str | None = None, destination_id: str | None = None
) -> list[AnnouncementPublic]:
    rows = announcement_repository.list_public_active(db, placement=placement, destination_id=destination_id)
    return [AnnouncementPublic.model_validate(o) for o in rows]


def record_event(db: Session, announcement_id: int, event: str) -> bool:
    """Suma una vista, clic o cierre. Atómico (UPDATE ... SET x = x + 1). False si no existe."""
    column = _EVENT_COLUMNS[event]
    result = db.execute(
        sql_update(Announcement)
        .where(Announcement.id == announcement_id)
        .values({column: getattr(Announcement, column) + 1})
        .execution_options(synchronize_session=False)
    )
    db.commit()
    return result.rowcount > 0
