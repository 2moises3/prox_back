"""
PROXVEL Backend - DB Traveler Profile Repository.
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config.database import SessionLocal
from app.models.traveler_profile_model import TravelerProfile

logger = logging.getLogger(__name__)

def get_profile_by_user_id(user_id: str) -> Optional[TravelerProfile]:
    try:
        db = SessionLocal()
        try:
            return db.scalar(select(TravelerProfile).where(TravelerProfile.user_id == user_id))
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching traveler profile: {e}")
        return None

def create_or_update_profile(user_id: str, profile_data: dict, is_partial: bool = False) -> Optional[TravelerProfile]:
    try:
        db = SessionLocal()
        try:
            profile = db.scalar(select(TravelerProfile).where(TravelerProfile.user_id == user_id))
            
            if not profile:
                # Si no existe y es PATCH, creamos uno nuevo vacío y le aplicamos los datos
                profile = TravelerProfile(user_id=user_id)
                db.add(profile)
            elif not is_partial:
                # Si existe y es PUT, limpiar todos los campos antes de aplicar (reemplazo)
                for column in profile.__table__.columns:
                    if column.name not in ["id", "user_id", "created_at", "updated_at"]:
                        setattr(profile, column.name, None)
            
            # Aplicar datos
            for key, value in profile_data.items():
                if is_partial and value is None:
                    continue # En PATCH ignoramos los None (no enviados)
                if hasattr(profile, key):
                    setattr(profile, key, value)
            
            db.commit()
            db.refresh(profile)
            return profile
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error saving traveler profile: {e}")
        return None
