"""
PROXVEL Backend - Recommendation Schemas.
Schemas Pydantic para endpoints de recomendaciones.
Adaptados a las columnas reales de ranking_contextual_final.csv.
Enriquecidos con datos del catálogo turístico (Fase 1B).
"""

from pydantic import BaseModel

from app.schemas.destination_schema import AspectScores, ContextScores


class RecommendationItem(BaseModel):
    """
    Item de recomendación contextual.
    Coincide con el contrato definido en el plan de implementación.
    """

    rank: int | None = None
    destination_id: str
    destination: str
    city: str | None = None
    region: str | None = None
    category: str | None = None
    cover_image_url: str | None = None
    compatibility_percentage: float | None = None
    label: str | None = None
    final_score: float | None = None
    short_explanation: str | None = None
    aspect_scores: AspectScores | None = None
    context: ContextScores | None = None
    tourism_summary: dict | None = None  # Fase 1B


class SearchResult(BaseModel):
    """Resultado de búsqueda de destino."""

    destination_id: str
    destination: str
    city: str | None = None
    region: str | None = None
    category: str | None = None
    cover_image_url: str | None = None
    compatibility_percentage: float | None = None
    final_score: float | None = None
