"""
PROXVEL Backend - Destination Schemas.
Schemas Pydantic para endpoints de destinos.
Adaptados a las columnas reales de los CSV de tesis.
Enriquecidos con datos del catálogo turístico (Fase 1B).
"""

from pydantic import BaseModel


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
    type: str | None = None
    subtype: str | None = None
    cover_image_url: str | None = None
    official_source_name: str | None = None
    is_active: bool = True
    data_status: str | None = None


class DestinationDetail(DestinationSummary):
    """Detalle completo de un destino con scores, contexto y turismo."""

    aspect_scores: AspectScores | None = None
    context: ContextScores | None = None
    weather_detail: WeatherDetail | None = None
    crowd_detail: CrowdDetail | None = None
    tourism_info: dict | None = None  # Fase 1B: info del catálogo turístico

class DestinationAdminUpdate(BaseModel):
    """Payload para actualización administrativa de un destino."""

    name: str | None = None
    city: str | None = None
    region: str | None = None
    category: str | None = None
    description: str | None = None
    official_source_name: str | None = None
    official_source_url: str | None = None


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
