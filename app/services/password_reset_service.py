"""
PROXVEL Backend - Recuperación de contraseña por correo.

Flujo: el usuario pide un código (6 dígitos) → llega por correo → lo ingresa con su nueva
contraseña. El código vence, sirve una sola vez y se bloquea tras varios intentos fallidos.

Seguridad:
  * Nunca se revela si un correo está registrado (la respuesta es siempre la misma).
  * Solo se guarda un HMAC del código, atado al usuario (no se puede reutilizar entre cuentas).
  * Pedir un código nuevo invalida los anteriores.
  * Restablecer cierra todas las sesiones abiertas (password_changed_at).
"""
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models.password_reset_model import PasswordResetCode
from app.models.user_model import User
from app.utils.hash_util import get_password_hash

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("proxvel.audit")

INVALID_CODE = "El código es incorrecto o ya venció."
TOO_MANY_ATTEMPTS = "Superaste los intentos permitidos. Pide un código nuevo."


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash(user_id: str, code: str) -> str:
    key = get_settings().SECRET_KEY.encode()
    return hmac.new(key, f"{user_id}:{code}".encode(), hashlib.sha256).hexdigest()


def _find_user(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def _eligible(user: User | None) -> bool:
    """Cuentas de sistema, desactivadas o en eliminación no pueden recuperar contraseña."""
    if user is None:
        return False
    if user.user_id == "ANON_DELETED" or user.email.endswith("@deleted.local") or user.email.endswith("@proxvel.internal"):
        return False
    return bool(user.is_active) and user.account_status == "active"


def request_code(db: Session, email: str, ip: str) -> tuple[User, str] | None:
    """
    Crea un código nuevo para el correo. Devuelve (usuario, código) para enviarlo,
    o None si el correo no existe o la cuenta no puede recuperarse (sin avisar al cliente).
    """
    user = _find_user(db, email)
    if not _eligible(user):
        audit_logger.info("AUDIT password_forgot IGNORED ip=%s reason=no_elegible", ip)
        return None

    now = _now()
    # Los códigos anteriores dejan de valer.
    db.execute(
        update(PasswordResetCode)
        .where(PasswordResetCode.user_id == user.user_id, PasswordResetCode.used_at.is_(None))
        .values(used_at=now)
    )
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(PasswordResetCode(
        user_id=user.user_id,
        code_hash=_hash(user.user_id, code),
        expires_at=now + timedelta(minutes=get_settings().PASSWORD_RESET_CODE_MINUTES),
        requested_ip=ip,
        created_at=now,
    ))
    db.commit()
    audit_logger.info("AUDIT password_forgot REQUESTED user=%s ip=%s", user.user_id, ip)
    return user, code


def confirm_code(db: Session, email: str, code: str, new_password: str, ip: str) -> tuple[bool, str | None]:
    """Valida el código y cambia la contraseña. Devuelve (ok, mensaje_de_error)."""
    user = _find_user(db, email)
    if not _eligible(user):
        audit_logger.warning("AUDIT password_reset DENIED ip=%s reason=cuenta_no_elegible", ip)
        return False, INVALID_CODE

    now = _now()
    row = db.scalar(
        select(PasswordResetCode)
        .where(PasswordResetCode.user_id == user.user_id, PasswordResetCode.used_at.is_(None))
        .order_by(PasswordResetCode.created_at.desc())
    )
    if row is None or row.expires_at < now:
        audit_logger.warning("AUDIT password_reset DENIED user=%s ip=%s reason=sin_codigo_vigente", user.user_id, ip)
        return False, INVALID_CODE

    if row.attempts >= get_settings().PASSWORD_RESET_MAX_ATTEMPTS:
        row.used_at = now
        db.commit()
        return False, TOO_MANY_ATTEMPTS

    if not hmac.compare_digest(row.code_hash, _hash(user.user_id, code)):
        row.attempts += 1
        burned = row.attempts >= get_settings().PASSWORD_RESET_MAX_ATTEMPTS
        if burned:
            row.used_at = now
        db.commit()
        audit_logger.warning("AUDIT password_reset DENIED user=%s ip=%s reason=codigo_incorrecto attempts=%s",
                             user.user_id, ip, row.attempts)
        return False, (TOO_MANY_ATTEMPTS if burned else INVALID_CODE)

    row.used_at = now
    user.password_hash = get_password_hash(new_password)
    user.password_changed_at = now
    db.commit()
    audit_logger.info("AUDIT password_reset OK user=%s ip=%s sessions_invalidated=true", user.user_id, ip)
    return True, None
