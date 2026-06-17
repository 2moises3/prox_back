"""
PROXVEL Backend - App Release Model (6B).
Metadata de versiones de la APK. El binario vive en storage externo
(Cloudinary raw o URL pública); aquí solo guardamos la metadata.
"""

from datetime import datetime

from sqlalchemy import String, Integer, Boolean, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AppRelease(Base, TimestampMixin):
    __tablename__ = "app_releases"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    version_name: Mapped[str] = mapped_column(String, nullable=False)   # ej. "1.0.0"
    version_code: Mapped[int] = mapped_column(Integer, nullable=False)  # ej. 1
    platform: Mapped[str] = mapped_column(String, default="android", index=True)

    apk_url: Mapped[str | None] = mapped_column(String)         # URL pública del binario
    file_public_id: Mapped[str | None] = mapped_column(String)  # id en Cloudinary (si aplica)
    file_size: Mapped[int | None] = mapped_column(Integer)      # bytes

    changelog: Mapped[str | None] = mapped_column(Text)

    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)

    created_by: Mapped[str | None] = mapped_column(String)
