"""
PROXVEL Backend - DB Visit Repository.
Acceso a datos de visitas y presencias en PostgreSQL.
"""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.models.visit_model import Visit
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog


def get_visit_by_id(visit_id: str, db: Optional[Session] = None) -> Optional[Visit]:
    own_session = db is None
    session = db or SessionLocal()
    try:
        stmt = select(Visit).where(Visit.visit_id == visit_id)
        return session.scalars(stmt).first()
    finally:
        if own_session:
            session.close()


def get_active_visit_by_user(user_id: str, destination_id: Optional[str] = None, db: Optional[Session] = None) -> Optional[Visit]:
    own_session = db is None
    session = db or SessionLocal()
    try:
        stmt = select(Visit).where(
            Visit.user_id == user_id,
            Visit.visit_status == "in_progress"
        )
        if destination_id:
            stmt = stmt.where(Visit.destination_id == destination_id)
        stmt = stmt.order_by(desc(Visit.started_at))
        return session.scalars(stmt).first()
    finally:
        if own_session:
            session.close()


def create_visit(
    visit_id: str,
    user_id: str,
    destination_id: str,
    entry_latitude: float,
    entry_longitude: float,
    validation_method: str = "gps_geofence",
    started_at: Optional[datetime] = None,
    db: Optional[Session] = None
) -> Visit:
    own_session = db is None
    session = db or SessionLocal()
    try:
        now = started_at or datetime.now(timezone.utc)
        visit = Visit(
            visit_id=visit_id,
            user_id=user_id,
            destination_id=destination_id,
            visit_status="in_progress",
            validation_method=validation_method,
            started_at=now,
            entry_latitude=entry_latitude,
            entry_longitude=entry_longitude,
            dwell_minutes=0
        )
        session.add(visit)
        session.commit()
        session.refresh(visit)
        return visit
    finally:
        if own_session:
            session.close()


def complete_visit(
    visit_id: str,
    dwell_minutes: int,
    completed_at: Optional[datetime] = None,
    db: Optional[Session] = None
) -> Optional[Visit]:
    own_session = db is None
    session = db or SessionLocal()
    try:
        visit = session.query(Visit).filter(Visit.visit_id == visit_id).first()
        if not visit:
            return None
        now = completed_at or datetime.now(timezone.utc)
        visit.visit_status = "verified"
        visit.completed_at = now
        visit.dwell_minutes = dwell_minutes
        session.commit()
        session.refresh(visit)
        return visit
    finally:
        if own_session:
            session.close()


def get_verified_visits_by_user(user_id: str, db: Optional[Session] = None) -> List[Visit]:
    own_session = db is None
    session = db or SessionLocal()
    try:
        stmt = (
            select(Visit)
            .where(
                Visit.user_id == user_id,
                Visit.visit_status == "verified"
            )
            .order_by(desc(Visit.completed_at))
        )
        return list(session.scalars(stmt).all())
    finally:
        if own_session:
            session.close()
