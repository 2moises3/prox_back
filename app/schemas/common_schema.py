"""
PROXVEL Backend - Common Schemas.
Schemas Pydantic compartidos: wrappers de respuesta, health, data status.
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class HealthResponse(BaseModel):
    """Respuesta del endpoint de salud."""

    status: str
    service: str
    version: str


class DataStatusResponse(BaseModel):
    """Estado de carga de cada archivo CSV."""

    matriz_absa_normalizada: bool
    clima_scores: bool
    aforo_scores: bool
    ranking_contextual_final: bool


class ApiResponse(BaseModel, Generic[T]):
    """Wrapper genérico de respuesta JSON estandarizada."""

    success: bool
    message: str
    data: T | None = None
    count: int | None = None
