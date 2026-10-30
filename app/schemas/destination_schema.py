"""
PROXVEL Backend - Destination Schemas.
Schemas Pydantic para endpoints de destinos.
Adaptados a las columnas reales de los CSV de tesis.
Enriquecidos con datos del catálogo turístico (Fase 1B).
"""

from pydantic import BaseModel, field_validator, computed_field


class AspectScores(BaseModel):
    """Puntajes ABSA normalizados por aspecto turístico."""

    accesibilidad: float | None = None
    aforo_multitudes: float | None = None
    alojamiento: float | None = None
    atencion_servicio: float | None = None
    atractivos: float | None = None
    clima: float | None = None
    costos: float | None = None
    gastronomia: float | None = None
    limpieza: float | None = None
    seguridad: float | None = None


class ContextScores(BaseModel):
    """Scores contextuales de clima y aforo."""

    weather_score: float | None = None
    crowd_score: float | None = None
    weather_category: str | None = None
    crowd_level: str | None = None


class WeatherDetail(BaseModel):
    """Detalle climático extendido."""

    month_name: str | None = None
    temp_prom: float | None = None
    pp: float | None = None
    clima_categoria: str | None = None
    score_clima: float | None = None


class CrowdDetail(BaseModel):
    """Detalle de aforo extendido."""

    periodo: str | None = None
    visitantes_mes: float | None = None
    aforo_normalizado: float | None = None
    nivel_aforo: str | None = None
    score_aforo_base: float | None = None


class DestinationSummary(BaseModel):
    """Resumen de un destino para listados. Enriquecido con catálogo (Fase 1B)."""

    destination_id: str
    destination: str
    city: str | None = None
    category: str | None = None
    region: str | None = None
    cover_image_url: str | None = None
    is_active: bool = True
    in_engine: bool = False
    @computed_field
    @property
    def scientific_version(self) -> str | None:
        from app.services.thesis_engine import get_engine, VERSION
        return VERSION if self.destination_id in get_engine().ids else None

    cost_level: str | None = None  # bajo | medio | alto (editorial)
    data_status: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class DestinationDetail(DestinationSummary):
    """Detalle completo de un destino con scores, contexto y turismo."""

    aspect_scores: AspectScores | None = None
    context: ContextScores | None = None
    weather_detail: WeatherDetail | None = None
    crowd_detail: CrowdDetail | None = None
    tourism_info: dict | None = None  # Fase 1B: info del catálogo turístico

class DestinationAdminUpdate(BaseModel):
    """Payload para actualización administrativa de la ficha comercial de un destino."""

    # Identidad
    name: str | None = None

    # Dónde está
    region: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: int | None = None

    # Qué es
    category: str | None = None
    description: str | None = None

    # Para decidir e ir
    activities_summary: str | None = None
    visitor_info_summary: str | None = None
    accessibility_summary: str | None = None
    recommended_duration: str | None = None
    how_to_get: str | None = None
    difficulty: str | None = None      # facil | moderada | exigente. null lo borra.
    official_website: str | None = None
    cost_level: str | None = None      # bajo | medio | alto. null lo borra.

    # Geolocalización y Atlas de Visitas
    geofence_radius_meters: int | None = None
    min_dwell_minutes: int | None = None

    @field_validator("cost_level")
    @classmethod
    def _valid_cost_level(cls, v):
        if v is None:
            return None
        v = v.strip().lower()
        if v == "":
            return None
        if v not in ("bajo", "medio", "alto"):
            raise ValueError("cost_level debe ser bajo, medio o alto.")
        return v

    @field_validator("difficulty")
    @classmethod
    def _valid_difficulty(cls, v):
        if v is None:
            return None
        v = v.strip().lower().replace("á", "a").replace("í", "i")
        if v == "":
            return None
        if v not in ("facil", "moderada", "exigente"):
            raise ValueError("difficulty debe ser facil, moderada o exigente.")
        return v


class DestinationAdminCreate(BaseModel):
    """Payload para crear un nuevo destino desde el panel admin."""

    name: str                          # Nombre visible del destino (requerido)
    destination_id: str | None = None  # Slug manual; si None, se genera desde name
    city: str | None = None
    region: str | None = None
    category: str | None = None
    description: str | None = None


class DestinationCreateResponse(BaseModel):
    """Respuesta mínima al crear un destino."""

    destination_id: str
    destination: str
    city: str | None = None
    region: str | None = None
    category: str | None = None


class DestinationStatusUpdate(BaseModel):
    """Payload para activar/desactivar un destino."""

    is_active: bool


class AbsaScoresUpdate(BaseModel):
    """Payload para actualizar puntajes ABSA (valores 0.0 – 1.0)."""

    accesibilidad: float | None = None
    aforo_multitudes: float | None = None
    alojamiento: float | None = None
    atencion_servicio: float | None = None
    atractivos: float | None = None
    clima: float | None = None
    costos: float | None = None
    gastronomia: float | None = None
    limpieza: float | None = None
    seguridad: float | None = None
