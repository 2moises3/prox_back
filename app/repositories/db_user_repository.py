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

def get_user_by_email(email: str) -> Optional[User]:
    try:
        db = SessionLocal()
        try:
            return db.scalar(select(User).where(User.email == email))
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching user by email: {e}")
        return None

def get_next_user_id() -> str:
    try:
        db = SessionLocal()
        try:
            last_user = db.scalar(select(User).order_by(User.user_id.desc()).limit(1))
            if not last_user or not last_user.user_id.startswith('U'):
                return "U00001"
            current_num = int(last_user.user_id[1:])
            return f"U{current_num + 1:05d}"
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error generating next user_id: {e}")
        return "U99999"

def create_user(user_id: str, name: Optional[str], email: str, password_hash: str) -> Optional[User]:
    try:
        db = SessionLocal()
        try:
            new_user = User(
                user_id=user_id,
                name=name,
                email=email,
                password_hash=password_hash,
                role="user",
                is_active=True
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            return new_user
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return None

def update_user(user_id: str, update_data: dict) -> Optional[User]:
    try:
        db = SessionLocal()
        try:
            user = db.scalar(select(User).where(User.user_id == user_id))
            if not user:
                return None
            for key, value in update_data.items():
                if value is not None:
                    setattr(user, key, value)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return None
