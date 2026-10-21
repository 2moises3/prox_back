"""
PROXVEL Backend - Announcement Repository.
Acceso a datos de la tabla announcements.
"""

from datetime import datetime, timezone

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from app.models.announcement_model import Announcement


def list_announcements(db: Session) -> list[Announcement]:
    stmt = select(Announcement).order_by(
        Announcement.priority.desc(), Announcement.created_at.desc()
    )
    return list(db.scalars(stmt).all())


def get_by_id(db: Session, announcement_id: int) -> Announcement | None:
    return db.get(Announcement, announcement_id)


def create(db: Session, data: dict) -> Announcement:
    obj = Announcement(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update(db: Session, obj: Announcement, updates: dict) -> Announcement:
    for key, value in updates.items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


def delete(db: Session, obj: Announcement) -> None:
    db.delete(obj)
    db.commit()


def list_public_active(
    db: Session, placement: str | None = None, destination_id: str | None = None
) -> list[Announcement]:
    """
    Anuncios visibles ahora: activos y dentro del rango de fechas.
    Ordenados por prioridad descendente. Con destination_id solo quedan los anuncios
    de ese destino o los que no apuntan a ninguno en particular.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    conditions = [
        Announcement.is_active.is_(True),
        or_(Announcement.starts_at.is_(None), Announcement.starts_at <= now),
        or_(Announcement.ends_at.is_(None), Announcement.ends_at >= now),
    ]
    if placement:
        conditions.append(Announcement.placement == placement)
    if destination_id:
        conditions.append(or_(
            Announcement.target_destination_id.is_(None),
            Announcement.target_destination_id == destination_id,
        ))

    stmt = (
        select(Announcement)
        .where(and_(*conditions))
        .order_by(Announcement.priority.desc(), Announcement.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def count_active(db: Session) -> int:
    return len(list_public_active(db))
