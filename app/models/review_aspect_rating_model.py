"""
PROXVEL Backend - Review Aspect Rating Model.
Ratings desagregados.
"""

from sqlalchemy import ForeignKey, String, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ReviewAspectRating(Base, TimestampMixin):
    __tablename__ = "review_aspect_ratings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.review_id"), index=True)
    
    aspect: Mapped[str] = mapped_column(String, nullable=False)
    rating: Mapped[float | None] = mapped_column(Float)
    comment: Mapped[str | None] = mapped_column(Text)

    # Relación
    review = relationship("Review", back_populates="aspect_ratings")
