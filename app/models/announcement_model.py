"""
PROXVEL Backend - Announcement Model.
Anuncios internos (in-app messages) administrados desde el dashboard y mostrados en la app móvil.
No integra redes publicitarias externas.
"""

from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Announcement(Base, TimestampMixin):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    title: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # app_start      → ventana al abrir la app (respeta frequency_cap)
    # home_top       → carrusel en Explorar (rota cada duration_seconds)
    # destination_detail → tarjeta dentro del detalle de un destino (o de todos)
    # global_modal   → aviso importante: se muestra al abrir hasta que el viajero lo confirma
    placement: Mapped[str] = mapped_column(String, default="app_start", index=True)
    # image_banner | gradient_card | minimal_notice | tourism_highlight | maintenance_notice
    template_type: Mapped[str] = mapped_column(String, default="gradient_card")

    background_image_url: Mapped[str | None] = mapped_column(String)
    media_public_id: Mapped[str | None] = mapped_column(String)

    # Acción del botón: ruta interna de la app ("/destination/machu_picchu", "/search", ...) o URL https.
    cta_text: Mapped[str | None] = mapped_column(String)
    cta_url: Mapped[str | None] = mapped_column(String)

    # Solo para placement=destination_detail: null = se muestra en todos los destinos.
    target_destination_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("destinations.destination_id", ondelete="SET NULL"), nullable=True
    )

    # Fechas en UTC (sin zona en la BD).
    starts_at: Mapped[datetime | None] = mapped_column(DateTime)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=5)

    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    # Máximo de veces que un mismo dispositivo ve el anuncio. null o 0 = sin límite.
    frequency_cap: Mapped[int | None] = mapped_column(Integer)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    audience: Mapped[str] = mapped_column(String, default="all")

    # Métricas agregadas que reporta la app.
    impressions: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    dismissals: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    created_by: Mapped[str | None] = mapped_column(String)
