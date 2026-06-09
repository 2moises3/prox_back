"""
PROXVEL Backend - Climate Score Model.
Contexto climático histórico (Fase 4).
"""

from sqlalchemy import ForeignKey, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ClimateScore(Base, TimestampMixin):
    __tablename__ = "climate_scores"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.destination_id"), index=True)
    
    month: Mapped[int] = mapped_column(Integer)
    temp_prom: Mapped[float | None] = mapped_column(Float)
    pp: Mapped[float | None] = mapped_column(Float)
    clima_categoria: Mapped[str | None] = mapped_column(String)
    score_clima: Mapped[float | None] = mapped_column(Float)

    # Relación inversa
    destination = relationship("Destination", back_populates="climate_scores")
