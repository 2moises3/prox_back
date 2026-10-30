"""
PROXVEL Backend - Visit Model.
Validación de presencia.
"""

from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Visit(Base, TimestampMixin):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    visit_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.destination_id"), index=True)
    
    visit_status: Mapped[str | None] = mapped_column(String)  # in_progress, verified, cancelled
    validation_method: Mapped[str | None] = mapped_column(String)  # gps_geofence, manual, qr

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dwell_minutes: Mapped[int | None] = mapped_column(Integer, default=0)
    entry_latitude: Mapped[float | None] = mapped_column(Float)
    entry_longitude: Mapped[float | None] = mapped_column(Float)

    # Relaciones
    user = relationship("User", back_populates="visits")
    destination_rel = relationship("Destination", back_populates="visits")
