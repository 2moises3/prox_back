"""
PROXVEL Backend - DB App Release Repository (6B).
"""
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.models.app_release_model import AppRelease

logger = logging.getLogger(__name__)


def get_all() -> List[AppRelease]:
    db = SessionLocal()
    try:
        return list(db.scalars(select(AppRelease).order_by(AppRelease.version_code.desc())).all())
    finally:
        db.close()


def get_by_id(release_id: int) -> Optional[AppRelease]:
    db = SessionLocal()
    try:
        return db.scalar(select(AppRelease).where(AppRelease.id == release_id))
    finally:
        db.close()


def create(data: dict[str, Any]) -> AppRelease:
    db = SessionLocal()
    try:
        release = AppRelease(**data)
        db.add(release)
        db.commit()
        db.refresh(release)
        return release
    finally:
        db.close()


def update(release_id: int, data: dict[str, Any]) -> Optional[AppRelease]:
    db = SessionLocal()
    try:
        release = db.scalar(select(AppRelease).where(AppRelease.id == release_id))
        if not release:
            return None
        for key, value in data.items():
            if value is not None and hasattr(release, key):
                setattr(release, key, value)
        db.commit()
        db.refresh(release)
        return release
    finally:
        db.close()


def set_published(release_id: int, is_published: bool) -> Optional[AppRelease]:
    """Publica/despublica. Al publicar, despublica las demás de la MISMA plataforma
    para garantizar una sola 'latest' por plataforma."""
    db = SessionLocal()
    try:
        release = db.scalar(select(AppRelease).where(AppRelease.id == release_id))
        if not release:
            return None

        if is_published:
            others = db.scalars(
                select(AppRelease)
                .where(AppRelease.platform == release.platform)
                .where(AppRelease.id != release.id)
                .where(AppRelease.is_published.is_(True))
            ).all()
            for o in others:
                o.is_published = False
                o.published_at = None
            release.is_published = True
            release.published_at = datetime.now(timezone.utc)
        else:
            release.is_published = False
            release.published_at = None

        db.commit()
        db.refresh(release)
        return release
    finally:
        db.close()


def delete(release_id: int) -> Optional[AppRelease]:
    db = SessionLocal()
    try:
        release = db.scalar(select(AppRelease).where(AppRelease.id == release_id))
        if not release:
            return None
        db.delete(release)
        db.commit()
        return release
    finally:
        db.close()


def get_latest_published(platform: str = "android") -> Optional[AppRelease]:
    db = SessionLocal()
    try:
        return db.scalar(
            select(AppRelease)
            .where(AppRelease.platform == platform)
            .where(AppRelease.is_published.is_(True))
            .order_by(AppRelease.version_code.desc())
        )
    finally:
        db.close()
