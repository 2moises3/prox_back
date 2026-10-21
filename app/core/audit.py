"""
PROXVEL Backend - Auditoría de seguridad en base de datos.

El logger "proxvel.audit" ya registra los eventos sensibles ("AUDIT <evento> user=… ip=…").
Este manejador además los guarda en la tabla audit_events para poder consultarlos y,
sobre todo, borrarlos al cumplirse AUDIT_RETENTION_DAYS (lo que promete la política de privacidad).
"""
import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import delete

from app.config.database import SessionLocal
from app.models.audit_event_model import AuditEvent

_EVENT = re.compile(r"^AUDIT\s+(\S+(?:\s+[A-Z_]+)?)")
_USER = re.compile(r"\buser=(\S+)")
_IP = re.compile(r"\bip=(\S+)")


class AuditDBHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = record.getMessage()
            if not msg.startswith("AUDIT"):
                return
            event = _EVENT.match(msg)
            user = _USER.search(msg)
            ip = _IP.search(msg)
            with SessionLocal() as db:
                db.add(AuditEvent(
                    event=(event.group(1) if event else "AUDIT")[:80],
                    user_id=user.group(1)[:40] if user else None,
                    ip=ip.group(1)[:64] if ip else None,
                    message=msg[:2000],
                ))
                db.commit()
        except Exception:  # la auditoría nunca debe romper la petición
            pass


def install_audit_handler() -> None:
    logger = logging.getLogger("proxvel.audit")
    logger.setLevel(logging.INFO)
    if not any(isinstance(h, AuditDBHandler) for h in logger.handlers):
        logger.addHandler(AuditDBHandler())


def purge_audit(days: int) -> int:
    """Borra los eventos de auditoría con más de `days` días. Devuelve cuántos borró."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    with SessionLocal() as db:
        result = db.execute(delete(AuditEvent).where(AuditEvent.created_at < cutoff))
        db.commit()
        return result.rowcount or 0
