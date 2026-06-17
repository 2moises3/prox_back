"""
PROXVEL Backend - Destination Model.
Modelo central de destinos.
"""

from sqlalchemy import String, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Destination(Base, TimestampMixin):
    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    destination_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)

    # Visibilidad pública. Inactivo = oculto en la app, visible en el dashboard.
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )

    # Relaciones
    tourism_catalog = relationship("TourismCatalog", back_populates="destination", uselist=False)
    aspect_scores = relationship("DestinationAspectScore", back_populates="destination", uselist=False)
    climate_scores = relationship("ClimateScore", back_populates="destination")
    crowd_scores = relationship("CrowdScore", back_populates="destination")
    contextual_rankings = relationship("ContextualRanking", back_populates="destination_rel")
    favorites = relationship("Favorite", back_populates="destination_rel")
    reviews = relationship("Review", back_populates="destination_rel")
    visits = relationship("Visit", back_populates="destination_rel")
