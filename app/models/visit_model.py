"""
PROXVEL Backend - Visit Model.
Validación de presencia.
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Visit(Base, TimestampMixin):
    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    visit_id: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.destination_id"), index=True)
    
    visit_status: Mapped[str | None] = mapped_column(String)
    validation_method: Mapped[str | None] = mapped_column(String)

    # Relaciones
    user = relationship("User", back_populates="visits")
    destination_rel = relationship("Destination", back_populates="visits")
