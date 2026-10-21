"""
PROXVEL Backend - Registro de auditoría de seguridad.
Guarda los eventos del logger "proxvel.audit" (acceso, contraseñas, eliminaciones, importaciones…)
con el usuario y la IP. Se purga pasados AUDIT_RETENTION_DAYS días (ver app/core/audit.py).
"""
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event: Mapped[str] = mapped_column(String(80), index=True)
    user_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
