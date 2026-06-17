"""
PROXVEL Backend - Announcement Model.
Anuncios internos / banners promocionales administrados desde el dashboard.
Pensados para consumirse luego desde la app móvil (overlay/Home).
No integra redes publicitarias externas.
"""

from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Announcement(Base, TimestampMixin):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # app_start | home_top | destination_detail | global_modal
    placement: Mapped[str] = mapped_column(String, default="app_start", index=True)
    # image_banner | gradient_card | minimal_notice | tourism_highlight | maintenance_notice
    template_type: Mapped[str] = mapped_column(String, default="gradient_card")

    background_image_url: Mapped[str | None] = mapped_column(String)
    media_public_id: Mapped[str | None] = mapped_column(String)

    cta_text: Mapped[str | None] = mapped_column(String)
    cta_url: Mapped[str | None] = mapped_column(String)

    starts_at: Mapped[datetime | None] = mapped_column(DateTime)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=5)

    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    frequency_cap: Mapped[int | None] = mapped_column(Integer)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    audience: Mapped[str] = mapped_column(String, default="all")

    created_by: Mapped[str | None] = mapped_column(String)
