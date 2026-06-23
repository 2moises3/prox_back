"""
PROXVEL Backend - Destination Tag Model.
Tags de interés por destino (cultura, gastronomia, aventura, etc.).
Reemplaza tags_destinos.csv / la sección tags_interes de destinos.json.
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DestinationTag(Base):
    __tablename__ = "destination_tags"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    destination_id: Mapped[str] = mapped_column(
        ForeignKey("destinations.destination_id"), index=True
    )
    tag: Mapped[str] = mapped_column(String, index=True)
