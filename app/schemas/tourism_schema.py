"""
PROXVEL Backend - Tourism Schemas.
Schemas Pydantic para el catálogo turístico oficial.
Información complementaria de MINCETUR que no afecta los scores de tesis.
"""

from pydantic import BaseModel


class TourismCatalogItem(BaseModel):
    """Item completo del catálogo turístico oficial."""

    destination_id: str
    destination: str
    official_name: str | None = None
    department: str | None = None
    province: str | None = None
    district: str | None = None
    city: str | None = None
    region: str | None = None
    category: str | None = None
    type: str | None = None
    subtype: str | None = None
    hierarchy: int | None = None
    altitude_m: int | None = None
    description: str | None = None
    experience_type: str | None = None
    visitor_info_summary: str | None = None
    activities_summary: str | None = None
    accessibility_summary: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    geofence_radius_m: float | None = None
    cover_image_url: str | None = None
    gallery_images: list[str] = []
    image_source: str | None = None
    image_license_note: str | None = None
    official_source_name: str | None = None
    official_source_code: str | None = None
    official_source_url: str | None = None
    secondary_source_name: str | None = None
    secondary_source_code: str | None = None
    secondary_source_url: str | None = None
    map_source: str | None = None
    data_status: str | None = None


class MapMarker(BaseModel):
    """Marcador de mapa con coordenadas válidas."""

    destination_id: str
    destination: str
    latitude: float
    longitude: float
    category: str | None = None
    label: str | None = None


class TourismInfo(BaseModel):
    """Información turística para enriquecer detalle de destino."""

    official_name: str | None = None
    description: str | None = None
    experience_type: str | None = None
    visitor_info_summary: str | None = None
    activities_summary: str | None = None
    accessibility_summary: str | None = None
    gallery_images: list[str] = []
    official_source_name: str | None = None
    official_source_url: str | None = None


class TourismSummary(BaseModel):
    """Resumen turístico breve para enriquecer recomendaciones."""

    description: str | None = None
    experience_type: str | None = None
    cover_image_url: str | None = None
