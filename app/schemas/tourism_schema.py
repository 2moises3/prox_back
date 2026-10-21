"""
PROXVEL Backend - Tourism Schemas.
Información comercial de los destinos (no afecta los scores de la tesis).
"""

from pydantic import BaseModel


class TourismCatalogItem(BaseModel):
    """Item completo del catálogo turístico."""

    destination_id: str
    destination: str
    region: str | None = None
    city: str | None = None
    category: str | None = None
    altitude_m: int | None = None
    description: str | None = None
    activities_summary: str | None = None
    visitor_info_summary: str | None = None
    accessibility_summary: str | None = None
    recommended_duration: str | None = None
    how_to_get: str | None = None
    difficulty: str | None = None
    official_website: str | None = None
    cost_level: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    cover_image_url: str | None = None
    gallery_images: list[str] = []
    data_status: str | None = None
    # Intereses de la tesis con los que encaja el destino (los mismos tags que usa el motor).
    interest_tags: list[str] = []


class MapMarker(BaseModel):
    """Marcador de mapa con coordenadas válidas."""

    destination_id: str
    destination: str
    latitude: float
    longitude: float
    category: str | None = None
    label: str | None = None


class TourismInfo(BaseModel):
    """Información turística para enriquecer el detalle de un destino."""

    description: str | None = None
    activities_summary: str | None = None
    visitor_info_summary: str | None = None
    accessibility_summary: str | None = None
    recommended_duration: str | None = None
    how_to_get: str | None = None
    difficulty: str | None = None
    official_website: str | None = None
    gallery_images: list[str] = []


class TourismSummary(BaseModel):
    """Resumen turístico breve para enriquecer recomendaciones."""

    description: str | None = None
    cover_image_url: str | None = None
