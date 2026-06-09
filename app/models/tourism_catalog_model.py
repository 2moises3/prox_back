"""
PROXVEL Backend - Tourism Catalog Model.
Catálogo oficial MINCETUR.
"""

from sqlalchemy import ForeignKey, String, Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TourismCatalog(Base, TimestampMixin):
    __tablename__ = "tourism_catalog"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    destination_id: Mapped[str] = mapped_column(ForeignKey("destinations.destination_id"), unique=True, index=True)
    
    official_name: Mapped[str | None] = mapped_column(String)
    department: Mapped[str | None] = mapped_column(String)
    province: Mapped[str | None] = mapped_column(String)
    district: Mapped[str | None] = mapped_column(String)
    city: Mapped[str | None] = mapped_column(String)
    region: Mapped[str | None] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String)
    type_: Mapped[str | None] = mapped_column("type", String) # Evitar palabra reservada type
    subtype: Mapped[str | None] = mapped_column(String)
    hierarchy: Mapped[int | None] = mapped_column(Integer)
    altitude_m: Mapped[int | None] = mapped_column(Integer)
    
    description: Mapped[str | None] = mapped_column(Text)
    experience_type: Mapped[str | None] = mapped_column(String)
    visitor_info_summary: Mapped[str | None] = mapped_column(Text)
    activities_summary: Mapped[str | None] = mapped_column(Text)
    accessibility_summary: Mapped[str | None] = mapped_column(Text)
    
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    geofence_radius_m: Mapped[float | None] = mapped_column(Float)
    
    cover_image_url: Mapped[str | None] = mapped_column(String)
    gallery_image_1: Mapped[str | None] = mapped_column(String)
    gallery_image_2: Mapped[str | None] = mapped_column(String)
    gallery_image_3: Mapped[str | None] = mapped_column(String)
    gallery_image_4: Mapped[str | None] = mapped_column(String)
    
    image_source: Mapped[str | None] = mapped_column(String)
    image_license_note: Mapped[str | None] = mapped_column(String)
    
    official_source_name: Mapped[str | None] = mapped_column(String)
    official_source_code: Mapped[str | None] = mapped_column(String)
    official_source_url: Mapped[str | None] = mapped_column(String)
    secondary_source_name: Mapped[str | None] = mapped_column(String)
    secondary_source_code: Mapped[str | None] = mapped_column(String)
    secondary_source_url: Mapped[str | None] = mapped_column(String)
    map_source: Mapped[str | None] = mapped_column(String)
    data_status: Mapped[str | None] = mapped_column(String)

    # Relación inversa
    destination = relationship("Destination", back_populates="tourism_catalog")
