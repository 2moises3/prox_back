"""
PROXVEL Backend - DB User Repository.
"""
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config.database import SessionLocal
from app.models.user_model import User

logger = logging.getLogger(__name__)

def get_demo_users() -> List[User]:
    try:
        db = SessionLocal()
        try:
            return list(db.scalars(select(User).where(User.role == "user")).all())
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return []

def get_user_by_id(user_id: str) -> Optional[User]:
    try:
        db = SessionLocal()
        try:
            return db.scalar(select(User).where(User.user_id == user_id))
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching user by id: {e}")
        return None
