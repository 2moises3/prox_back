"""
PROXVEL Backend - User Model.
Base para registro y autenticación.
"""

from datetime import datetime
from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="traveler")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    avatar_url: Mapped[str | None] = mapped_column(String)

    # Ubicación base del usuario (Residencia)
    residence_department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    residence_province: Mapped[str | None] = mapped_column(String(120), nullable=True)
    residence_city: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Ciclo de vida (Fase 0.3)
    account_status: Mapped[str] = mapped_column(String, default="active")
    deletion_requested_at: Mapped[datetime | None] = mapped_column(DateTime)
    deletion_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    deletion_reason: Mapped[str | None] = mapped_column(String)
    deletion_requested_by: Mapped[str | None] = mapped_column(String)

    # Última vez que un administrador restableció la contraseña. Los tokens emitidos antes
    # (claim iat) dejan de ser válidos: cierra las sesiones abiertas.
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Consentimiento: versión de Términos y Política de Privacidad aceptada y cuándo
    # (el viajero declara además ser mayor de 18 años en esa misma aceptación).
    accepted_terms_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    accepted_terms_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relaciones
    traveler_profiles = relationship("TravelerProfile", back_populates="user")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    archives = relationship("Archive", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="user")
    visits = relationship("Visit", back_populates="user")
