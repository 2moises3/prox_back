"""
PROXVEL Backend - Model Update Run Model.
Historial de procesos de entrenamiento externo.
"""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ModelUpdateRun(Base, TimestampMixin):
    __tablename__ = "model_update_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    run_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    batch_id: Mapped[str] = mapped_column(ForeignKey("monthly_review_batches.batch_id"), index=True)
    
    model_name: Mapped[str | None] = mapped_column(String)
    metrics_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String)

    # Relación
    batch = relationship("MonthlyReviewBatch", back_populates="model_update_runs")
