"""
PROXVEL Backend - Contextual Ranking Model.
Resultados finales Fase 4 precalculados.
"""

from sqlalchemy import ForeignKey, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ContextualRanking(Base, TimestampMixin):
    __tablename__ = "contextual_rankings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.destination_id"), index=True)
    
    rank: Mapped[int | None] = mapped_column(Integer)
    score_final_fase4: Mapped[float | None] = mapped_column(Float)
    compatibilidad_final: Mapped[float | None] = mapped_column(Float)
    etiqueta_final: Mapped[str | None] = mapped_column(String)
    explicacion_final: Mapped[str | None] = mapped_column(Text)

    # Relación inversa
    destination_rel = relationship("Destination", back_populates="contextual_rankings")
