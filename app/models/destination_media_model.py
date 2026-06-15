"""
PROXVEL Backend - Destination Media Model.
Tabla para gestionar imágenes y videos asociados a destinos turísticos.
Preparado para futura integración con Cloudinary.
"""

from sqlalchemy import ForeignKey, String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DestinationMedia(Base, TimestampMixin):
    __tablename__ = "destination_media"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.destination_id"), index=True)
    
    media_type: Mapped[str] = mapped_column(String)  # 'cover' o 'gallery'
    provider: Mapped[str] = mapped_column(String)    # 'cloudinary', 'external', 'local'
    public_id: Mapped[str | None] = mapped_column(String)
    url: Mapped[str | None] = mapped_column(String)
    
    position: Mapped[int] = mapped_column(Integer, default=0)
    alt_text: Mapped[str | None] = mapped_column(String)
    credit: Mapped[str | None] = mapped_column(String)
    license_note: Mapped[str | None] = mapped_column(String)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    # Relaciones inversas
    destination = relationship("Destination")
    uploaded_by = relationship("User")
