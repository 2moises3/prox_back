"""
PROXVEL Backend - User Admin Service (6B).
Gestión administrativa de usuarios: listar, cambiar rol, activar/desactivar.
Incluye guardas para no dejar el sistema sin super_admin y no permitir
auto-desactivación.

Extensión 6B: creación de usuarios desde dashboard y eliminación segura.
"""
import logging
from typing import List, Optional

from app.config.database import SessionLocal
from app.repositories import db_user_repository
from app.schemas.user_schema import (
    UserResponse,
    AdminUserResponse,
    ALLOWED_ROLES,
    DASHBOARD_CREATABLE_ROLES,
)
from app.utils.hash_util import get_password_hash

logger = logging.getLogger(__name__)


def list_users() -> List[AdminUserResponse]:
    users = db_user_repository.get_all_users()
    return [AdminUserResponse.model_validate(u) for u in users]


def change_user_role(
    target_user_id: str, new_role: str, acting_user_id: str
) -> tuple[Optional[UserResponse], Optional[str]]:
    if new_role not in ALLOWED_ROLES:
        return None, f"Rol inválido. Use uno de: {', '.join(ALLOWED_ROLES)}"

    # Guarda: nadie cambia su propio rol (incluye auto-ascenso a super_admin).
    if target_user_id == acting_user_id:
        return None, "No puedes cambiar tu propio rol."

    target = db_user_repository.get_user_by_id(target_user_id)
    if not target:
        return None, "Usuario no encontrado"

    if target.role == new_role:
        return UserResponse.model_validate(target), None

    # Guarda: no degradar al último super_admin activo.
    if target.role == "super_admin" and new_role != "super_admin" and target.is_active:
        if db_user_repository.count_active_super_admins() <= 1:
            return None, "No puedes quitar el rol del último super_admin activo."

    updated = db_user_repository.update_user(target_user_id, {"role": new_role})
    if updated:
        return UserResponse.model_validate(updated), None
    return None, "Error interno al actualizar el rol"


def change_user_status(
    target_user_id: str, is_active: bool, acting_user_id: str
) -> tuple[Optional[UserResponse], Optional[str]]:
    target = db_user_repository.get_user_by_id(target_user_id)
    if not target:
        return None, "Usuario no encontrado"

    # Guarda: no auto-desactivarse.
    if not is_active and target_user_id == acting_user_id:
        return None, "No puedes desactivar tu propia cuenta."

    # Guarda: no desactivar al último super_admin activo.
    if not is_active and target.role == "super_admin" and target.is_active:
        if db_user_repository.count_active_super_admins() <= 1:
            return None, "No puedes desactivar al último super_admin activo."

    if target.is_active == is_active:
        return UserResponse.model_validate(target), None

    updated = db_user_repository.update_user(target_user_id, {"is_active": is_active})
    if updated:
        return UserResponse.model_validate(updated), None
    return None, "Error interno al actualizar el estado"


# ── Extensión 6B: Creación de usuarios desde dashboard ───────────────────────


def create_user_admin(
    name: str, email: str, password: str, role: str
) -> tuple[Optional[AdminUserResponse], Optional[str], Optional[int]]:
    """
    Crea un usuario desde el dashboard.
    Retorna (user, error_message, http_status_code).
    """
    # Validar rol: solo admin y traveler permitidos desde dashboard
    if role not in DASHBOARD_CREATABLE_ROLES:
        return None, "No se permite crear super_admin desde el dashboard.", 403

    # Validar email único
    existing = db_user_repository.get_user_by_email(email)
    if existing:
        return None, f"Ya existe un usuario con el email '{email}'.", 409

    # Hashear password
    password_hash = get_password_hash(password)

    # Generar user_id y crear
    user_id = db_user_repository.get_next_user_id()

    db = SessionLocal()
    try:
        from app.models.user_model import User

        new_user = User(
            user_id=user_id,
            name=name,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return AdminUserResponse.model_validate(new_user), None, None
    except Exception as e:
        db.rollback()
        logger.error(f"Error creando usuario admin: {e}")
        return None, "Error interno al crear el usuario.", 500
    finally:
        db.close()


# ── Extensión 6B: Eliminación segura de usuarios ─────────────────────────────


def delete_user(
    target_user_id: str, mode: str, acting_user_id: str
) -> tuple[Optional[dict], Optional[str], Optional[int]]:
    """
    Elimina datos o cuenta de un usuario.
    mode: 'data_only' | 'full'
    Retorna (result_dict, error_message, http_status_code).
    """
    if mode not in ("data_only", "full"):
        return None, f"Modo inválido '{mode}'. Use 'data_only' o 'full'.", 422

    # Guarda: no auto-eliminarse
    if target_user_id == acting_user_id:
        return None, "No puedes eliminar tu propia cuenta.", 409

    target = db_user_repository.get_user_by_id(target_user_id)
    if not target:
        return None, "Usuario no encontrado.", 404

    # Guarda: no eliminar super_admin
    if target.role == "super_admin":
        return None, "No se puede eliminar una cuenta super_admin desde el dashboard.", 403

    # Ejecutar en transacción
    db = SessionLocal()
    try:
        counts = db_user_repository.delete_user_data(db, target_user_id)

        if mode == "full":
            db_user_repository.delete_user_record(db, target_user_id)
            counts["account_deleted"] = True
        else:
            counts["account_deleted"] = False

        db.commit()

        action = "eliminada" if mode == "full" else "limpiada"
        return counts, None, None

    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando usuario {target_user_id} (mode={mode}): {e}")
        return None, "Error interno al procesar la eliminación.", 500
    finally:
        db.close()


# ── Detalles de usuario ──────────────────────────────────────────────────────

def get_user_details_admin(user_id: str) -> tuple[Optional[dict], Optional[str], Optional[int]]:
    db = SessionLocal()
    try:
        from app.models.user_model import User
        from app.models.favorite_model import Favorite
        from app.models.traveler_profile_model import TravelerProfile

        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return None, "Usuario no encontrado.", 404

        fav_count = db.query(Favorite).filter(Favorite.user_id == user_id).count()
        profile = db.query(TravelerProfile).filter(TravelerProfile.user_id == user_id).first()

        aspects = []
        if profile and profile.aspects:
            aspects = profile.aspects

        return {
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "avatar_url": user.avatar_url,
            "favorites_count": fav_count,
            "aspects": aspects
        }, None, None
    except Exception as e:
        logger.error(f"Error obteniendo detalles del usuario {user_id}: {e}")
        return None, "Error interno al obtener detalles.", 500
    finally:
        db.close()
