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
            return list(db.scalars(select(User).where(User.role == "traveler")).all())
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        return []

def get_all_users() -> List[User]:
    """Lista todos los usuarios (cualquier rol), ordenados por user_id."""
    try:
        db = SessionLocal()
        try:
            return list(db.scalars(select(User).order_by(User.user_id.asc())).all())
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error listing all users: {e}")
        return []


def count_active_super_admins() -> int:
    """Cuenta super_admins activos (para no permitir quedarse sin ninguno)."""
    try:
        db = SessionLocal()
        try:
            rows = db.scalars(
                select(User).where(User.role == "super_admin").where(User.is_active.is_(True))
            ).all()
            return len(list(rows))
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error counting super admins: {e}")
        return 0


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
                role="traveler",
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
                setattr(user, key, value)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return None

def update_password_hash(user_id: str, new_password_hash: str) -> bool:
    """Actualiza exclusivamente el password_hash de un usuario de forma segura."""
    try:
        db = SessionLocal()
        try:
            user = db.scalar(select(User).where(User.user_id == user_id))
            if not user:
                return False
            user.password_hash = new_password_hash
            db.commit()
            return True
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error updating password hash: {e}")
        return False


# ── Extensión 6B: Eliminación segura de usuarios ─────────────────────────────

ANON_USER_ID = "ANON_DELETED"


def ensure_anon_sentinel(db: Session) -> None:
    """Crea el usuario centinela ANON_DELETED si no existe (idempotente)."""
    existing = db.scalar(select(User).where(User.user_id == ANON_USER_ID))
    if existing:
        return
    sentinel = User(
        user_id=ANON_USER_ID,
        name="Viajero eliminado",
        email="deleted@proxvel.internal",
        password_hash="no_login",
        role="traveler",
        is_active=False,
    )
    db.add(sentinel)
    db.flush()
    logger.info("Usuario centinela ANON_DELETED creado.")


def delete_user_data(db: Session, user_id: str) -> dict:
    """
    Elimina datos asociados a un usuario y anonimiza sus reseñas.
    Recibe una sesión externa para control transaccional.
    Retorna un dict con los contadores de registros afectados.
    """
    from app.models.favorite_model import Favorite
    from app.models.visit_model import Visit
    from app.models.traveler_profile_model import TravelerProfile
    from app.models.contextual_ranking_model import ContextualRanking
    from app.models.review_model import Review

    counts: dict = {}

    # 1. Favoritos
    fav_count = db.query(Favorite).filter(Favorite.user_id == user_id).delete(synchronize_session="fetch")
    counts["favorites_deleted"] = fav_count

    # 2. Visitas
    visit_count = db.query(Visit).filter(Visit.user_id == user_id).delete(synchronize_session="fetch")
    counts["visits_deleted"] = visit_count

    # 3. Perfiles de viajero
    profile_count = db.query(TravelerProfile).filter(TravelerProfile.user_id == user_id).delete(synchronize_session="fetch")
    counts["profiles_deleted"] = profile_count

    # 4. Rankings contextuales (user_id es String plano, sin FK)
    ranking_count = db.query(ContextualRanking).filter(ContextualRanking.user_id == user_id).delete(synchronize_session="fetch")
    counts["rankings_deleted"] = ranking_count

    # 5. Anonimizar reseñas (reasignar al centinela)
    ensure_anon_sentinel(db)
    review_count = db.query(Review).filter(Review.user_id == user_id).update(
        {Review.user_id: ANON_USER_ID}, synchronize_session="fetch"
    )
    counts["reviews_anonymized"] = review_count

    db.flush()
    return counts


def delete_user_record(db: Session, user_id: str) -> bool:
    """Elimina el registro del usuario de la tabla users. Retorna True si se eliminó."""
    deleted = db.query(User).filter(User.user_id == user_id).delete(synchronize_session="fetch")
    db.flush()
    return deleted > 0

