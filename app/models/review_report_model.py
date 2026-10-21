"""
PROXVEL Backend - Reportes de reseñas.
Un viajero puede reportar una reseña ofensiva; el dashboard la marca y permite ocultarla.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ReviewReport(Base):
    __tablename__ = "review_reports"
    __table_args__ = (UniqueConstraint("review_id", "reporter_user_id", name="uq_review_report_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    review_id: Mapped[str] = mapped_column(ForeignKey("reviews.review_id", ondelete="CASCADE"), index=True)
    reporter_user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    reason: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
