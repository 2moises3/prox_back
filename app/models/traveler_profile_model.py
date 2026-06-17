"""
PROXVEL Backend - Traveler Profile Model.
Preferencias estáticas del viajero.
"""

from sqlalchemy import ForeignKey, String, Float, Integer, JSON, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TravelerProfile(Base, TimestampMixin):
    __tablename__ = "traveler_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    
    presupuesto: Mapped[str | None] = mapped_column(String)
    dias_viaje: Mapped[int | None] = mapped_column(Integer)
    clima_preferido: Mapped[str | None] = mapped_column(String)
    tipo_interes: Mapped[str | None] = mapped_column(String)
    intereses: Mapped[list[str] | None] = mapped_column(JSON)
    tolerancia_multitudes: Mapped[str | None] = mapped_column(String)

    # Preferencia: aplicar recomendación IA en toda la app (Explorar/Search/Detalle).
    # No afecta la pestaña "Para ti", que es IA por definición. Default: False.
    apply_ai_globally: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )

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
