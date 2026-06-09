"""
PROXVEL Backend - Crowd Score Model.
Contexto de aforo extraído del CSV real (Fase 4).
"""

from sqlalchemy import ForeignKey, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class CrowdScore(Base, TimestampMixin):
    __tablename__ = "crowd_scores"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.destination_id"), index=True)
    
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    visitantes_mes: Mapped[float | None] = mapped_column(Float)
    aforo_normalizado: Mapped[float | None] = mapped_column(Float)
    nivel_aforo: Mapped[str | None] = mapped_column(String)
    score_aforo_base: Mapped[float | None] = mapped_column(Float)
    periodo: Mapped[str | None] = mapped_column(String)

    # Relación inversa
    destination = relationship("Destination", back_populates="crowd_scores")
