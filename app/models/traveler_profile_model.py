"""
PROXVEL Backend - Traveler Profile Model.
Preferencias estáticas del viajero.
"""

from sqlalchemy import ForeignKey, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TravelerProfile(Base, TimestampMixin):
    __tablename__ = "traveler_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    
    presupuesto: Mapped[str | None] = mapped_column(String)
    clima_preferido: Mapped[str | None] = mapped_column(String)
    tolerancia_multitudes: Mapped[str | None] = mapped_column(String)
    
    # Pesos ABSA
    peso_accesibilidad: Mapped[float | None] = mapped_column(Float)
    peso_aforo_multitudes: Mapped[float | None] = mapped_column(Float)
    peso_alojamiento: Mapped[float | None] = mapped_column(Float)
    peso_atencion_servicio: Mapped[float | None] = mapped_column(Float)
    peso_atractivos: Mapped[float | None] = mapped_column(Float)
    peso_clima: Mapped[float | None] = mapped_column(Float)
    peso_costos: Mapped[float | None] = mapped_column(Float)
    peso_gastronomia: Mapped[float | None] = mapped_column(Float)
    peso_limpieza: Mapped[float | None] = mapped_column(Float)
    peso_seguridad: Mapped[float | None] = mapped_column(Float)

    # Relación inversa
    user = relationship("User", back_populates="traveler_profiles")
