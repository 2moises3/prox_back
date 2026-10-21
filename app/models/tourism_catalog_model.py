"""
PROXVEL Backend - Tourism Catalog Model.
Información comercial de cada destino (lo que el viajero necesita para decidir e ir).
Las imágenes viven en destination_media; el motor de recomendación no usa estos campos.
"""

from sqlalchemy import ForeignKey, String, Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TourismCatalog(Base, TimestampMixin):
    __tablename__ = "tourism_catalog"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.destination_id"), unique=True, index=True)

    # Dónde está
    region: Mapped[str | None] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String)          # ciudad base o más cercana
    latitude: Mapped[float | None] = mapped_column(Float)      # pin de Google Maps (punto de acceso)
    longitude: Mapped[float | None] = mapped_column(Float)
    altitude_m: Mapped[int | None] = mapped_column(Integer)

    # Qué es
    category: Mapped[str | None] = mapped_column(String)       # Arqueología | Naturaleza | Museo | Recreación
    description: Mapped[str | None] = mapped_column(Text)

    # Para decidir e ir
    activities_summary: Mapped[str | None] = mapped_column(Text)
    visitor_info_summary: Mapped[str | None] = mapped_column(Text)
    accessibility_summary: Mapped[str | None] = mapped_column(Text)
    recommended_duration: Mapped[str | None] = mapped_column(String)   # p. ej. "Medio día"
    how_to_get: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[str | None] = mapped_column(String)             # facil | moderada | exigente
    official_website: Mapped[str | None] = mapped_column(String)       # sitio oficial o de entradas
    cost_level: Mapped[str | None] = mapped_column(String)             # bajo | medio | alto

    # Uso interno del dashboard
    data_status: Mapped[str | None] = mapped_column(String)

    destination = relationship("Destination", back_populates="tourism_catalog")
