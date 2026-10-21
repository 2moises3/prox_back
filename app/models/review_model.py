"""
PROXVEL Backend - Review Model.
Reseñas libres enviadas por el usuario.
"""

from sqlalchemy import ForeignKey, String, Integer, Text, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    review_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.destination_id"), index=True)
    
    rating_general: Mapped[float | None] = mapped_column(Float)
    review_text: Mapped[str | None] = mapped_column(Text)
    visit_date: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, default="app")
    language: Mapped[str] = mapped_column(String, default="es")
    is_verified_visit: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_method: Mapped[str] = mapped_column(String, default="self_report_pending")
    
    # Estados: pending_processing, exported, processed, discarded
    # Oculta por moderación (tras reportes): no se muestra a otros viajeros ni entra al entrenamiento.
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending_processing")
    processing_month: Mapped[str | None] = mapped_column(String)  # ej: "2026-06"
    training_batch_id: Mapped[str | None] = mapped_column(ForeignKey("monthly_review_batches.batch_id"), nullable=True)

    # Relaciones
    user = relationship("User", back_populates="reviews")
    destination_rel = relationship("Destination", back_populates="reviews")
    aspect_ratings = relationship("ReviewAspectRating", back_populates="review")
    training_batch = relationship("MonthlyReviewBatch", back_populates="reviews")
