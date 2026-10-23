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


class RecommendationEngineInfo(BaseModel):
    source: str
    version: str
    is_final_model: bool
    metrics_status: str

class RecommendationAspectContribution(BaseModel):
    aspect: str
    user_weight: float
    destination_score: float
    contribution: float

class RecommendationExplanation(BaseModel):
    summary: str
    top_aspects: list[RecommendationAspectContribution]
    shap_base: float | None = None
    shap_values: dict[str, float] | None = None
    shap_method: str | None = None

class RecommendationMeItem(BaseModel):
    destination_id: str
    name: str
    city: str | None = None
    region: str | None = None
    category: str | None = None
    cover_image_url: str | None = None
    rating: float | None = None
    label_code: str | None = None
    perfil_turistico: str | None = None
    affinity_f3: float | None = None
    coverage: float | None = None
    quality_absa: float | None = None
    climate_score: float | None = None
    crowd_score: float | None = None
    score_semantics: str | None = None
    compatibility_score: float
    compatibility_percent: int
    label: str | None = None
    month: int | None = None
    month_name: str | None = None
    best_month: int | None = None
    best_month_name: str | None = None
    context_status: str | None = None
    ranking_position: int
    has_real_scores: bool | None = None
    explanation: RecommendationExplanation

class RecommendationMeResponse(BaseModel):
    success: bool = True
    message: str
    engine: RecommendationEngineInfo
    data: list[RecommendationMeItem]
