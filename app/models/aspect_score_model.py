"""
PROXVEL Backend - Destination Aspect Score Model.
Resultados ABSA por destino.
"""

from sqlalchemy import ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DestinationAspectScore(Base, TimestampMixin):
    __tablename__ = "destination_aspect_scores"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.destination_id"), unique=True, index=True)
    
    accesibilidad: Mapped[float | None] = mapped_column(Float)
    aforo_multitudes: Mapped[float | None] = mapped_column(Float)
    alojamiento: Mapped[float | None] = mapped_column(Float)
    atencion_servicio: Mapped[float | None] = mapped_column(Float)
    atractivos: Mapped[float | None] = mapped_column(Float)
    clima: Mapped[float | None] = mapped_column(Float)
    costos: Mapped[float | None] = mapped_column(Float)
    gastronomia: Mapped[float | None] = mapped_column(Float)
    limpieza: Mapped[float | None] = mapped_column(Float)
    seguridad: Mapped[float | None] = mapped_column(Float)

    # Relación inversa
    destination = relationship("Destination", back_populates="aspect_scores")
