"""
PROXVEL Backend - Monthly Review Batch Model.
Lotes para exportación de MLOps.
"""

from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MonthlyReviewBatch(Base, TimestampMixin):
    __tablename__ = "monthly_review_batches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    batch_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    total_reviews: Mapped[int | None] = mapped_column(Integer, default=0)
    
    # Estados: created, exported, used_for_training, closed
    status: Mapped[str] = mapped_column(String, default="created")
    export_path: Mapped[str | None] = mapped_column(String)

    # Relaciones
    reviews = relationship("Review", back_populates="training_batch")
    model_update_runs = relationship("ModelUpdateRun", back_populates="batch")
