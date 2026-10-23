"""
PROXVEL Backend - Traveler Profile Schemas.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Literal

class TravelerProfileBase(BaseModel):
    perfil_turistico: Literal["cultural", "naturalista", "familiar", "economico_mochilero", "gastronomico", "aventurero", "urbano_recreativo"] | None = None
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

class _TravelerProfileInput(TravelerProfileBase):
    @field_validator('intereses')
    @classmethod
    def validate_interests(cls, values):
        if values is None: return values
        from app.services.thesis_engine import get_engine, normalize
        aliases = {'cultural':'cultura','gastronomico':'gastronomia'}
        result = list(dict.fromkeys(aliases.get(normalize(v),normalize(v)) for v in values))
        if set(result) - set(get_engine().interests):
            raise ValueError('Selecciona intereses del catálogo disponible')
        return result

    @field_validator('clima_preferido')
    @classmethod
    def validate_climate(cls, value):
        if value is None: return value
        from app.services.thesis_engine import get_engine, normalize
        value = normalize(value)
        if value not in get_engine().climate: raise ValueError('Selecciona un clima válido')
        return value

    @field_validator('tolerancia_multitudes')
    @classmethod
    def validate_tolerance(cls, value):
        if value is None: return value
        from app.services.thesis_engine import normalize
        value = normalize(value)
        value = {'bajo':'baja','medio':'media','alto':'alta','moderado':'media'}.get(value,value)
        if value not in ('baja','media','alta'): raise ValueError('Selecciona una tolerancia válida')
        return value

class TravelerProfileCreate(_TravelerProfileInput):
    pass

class TravelerProfileUpdate(_TravelerProfileInput):
    pass

class TravelerProfileResponse(TravelerProfileBase):
    user_id: str

    class Config:
        from_attributes = True
