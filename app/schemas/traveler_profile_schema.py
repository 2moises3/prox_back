"""
PROXVEL Backend - Traveler Profile Schemas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List

class TravelerProfileBase(BaseModel):
    presupuesto: Optional[str] = None
    dias_viaje: Optional[int] = None
    clima_preferido: Optional[str] = None
    tipo_interes: Optional[str] = None
    intereses: Optional[List[str]] = Field(default_factory=list)
    tolerancia_multitudes: Optional[str] = None

    # Preferencia global de IA. No apaga la pestaña "Para ti".
    apply_ai_globally: Optional[bool] = False

    peso_accesibilidad: Optional[float] = Field(None, ge=1.0, le=5.0)
    peso_aforo_multitudes: Optional[float] = Field(None, ge=1.0, le=5.0)
    peso_alojamiento: Optional[float] = Field(None, ge=1.0, le=5.0)
    peso_atencion_servicio: Optional[float] = Field(None, ge=1.0, le=5.0)
    peso_atractivos: Optional[float] = Field(None, ge=1.0, le=5.0)
    peso_clima: Optional[float] = Field(None, ge=1.0, le=5.0)
    peso_costos: Optional[float] = Field(None, ge=1.0, le=5.0)
    peso_gastronomia: Optional[float] = Field(None, ge=1.0, le=5.0)
    peso_limpieza: Optional[float] = Field(None, ge=1.0, le=5.0)
    peso_seguridad: Optional[float] = Field(None, ge=1.0, le=5.0)

class TravelerProfileCreate(TravelerProfileBase):
    pass

class TravelerProfileUpdate(TravelerProfileBase):
    pass

class TravelerProfileResponse(TravelerProfileBase):
    user_id: str

    class Config:
        from_attributes = True
