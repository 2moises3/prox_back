"""
PROXVEL Backend - Notification Models.
Centro de notificaciones de la app: avisos personales por usuario y registro de qué
anuncios del dashboard ya leyó cada usuario.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Notification(Base, TimestampMixin):
    """Aviso personal (mejor mes de un favorito, perfil listo, seguridad, destino nuevo...)."""

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "dedupe_key", name="uq_notification_user_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Ruta interna de la app a la que lleva el aviso (p. ej. /destination/machu_picchu).
    route: Mapped[str | None] = mapped_column(String)
    destination_id: Mapped[str | None] = mapped_column(String)
    # Evita crear el mismo aviso dos veces (p. ej. "mejor mes" de un favorito en un mes dado).
    dedupe_key: Mapped[str | None] = mapped_column(String)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)


class NotificationPreference(Base):
    """Account-scoped visibility choices for the in-app notification centre."""
    __tablename__ = "notification_preferences"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    recommendations: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    new_destinations: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    announcements: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")


class AnnouncementRead(Base):
    """Anuncio del dashboard que un usuario ya marcó como leído."""

    __tablename__ = "announcement_reads"
    __table_args__ = (
        UniqueConstraint("user_id", "announcement_id", name="uq_announcement_read"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True, nullable=False
    )
    announcement_id: Mapped[int] = mapped_column(
        ForeignKey("announcements.id", ondelete="CASCADE"), index=True, nullable=False
    )
    read_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
