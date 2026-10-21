"""
PROXVEL Backend - Engine Schemas.
Parámetros del motor de recomendación y participación de destinos.
"""
from pydantic import BaseModel, Field, model_validator


class EngineConfigUpdate(BaseModel):
    """Parámetros editables del motor (valores de la tesis entre paréntesis)."""

    alpha_absa: float = Field(..., ge=0.0, le=1.0, description="Peso de ABSA en la afinidad (0.25)")
    beta_contexto: float = Field(..., ge=0.0, le=1.0, description="Peso del contexto clima/aforo (0.30)")
    w_clima: float = Field(..., ge=0.0, le=1.0, description="Peso del clima dentro del contexto (0.5)")
    w_aforo: float = Field(..., ge=0.0, le=1.0, description="Peso del aforo dentro del contexto (0.5)")

    @model_validator(mode="after")
    def _context_weights_sum_one(self):
        if abs(self.w_clima + self.w_aforo - 1.0) > 0.001:
            raise ValueError("w_clima y w_aforo deben sumar 1.")
        return self


class EngineMembershipUpdate(BaseModel):
    in_engine: bool
