"""
PROXVEL Backend - Announcement Schemas.
Validación y serialización de anuncios internos.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# Valores permitidos (alineados con el dashboard)
PLACEMENTS = ("app_start", "home_top", "destination_detail", "global_modal")
TEMPLATES = (
    "image_banner",
    "gradient_card",
    "minimal_notice",
    "tourism_highlight",
    "maintenance_notice",
)


class AnnouncementBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    message: str = Field(..., min_length=1)
    placement: str = "app_start"
    template_type: str = "gradient_card"
    background_image_url: Optional[str] = None
    media_public_id: Optional[str] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    duration_seconds: int = Field(5, ge=1, le=120)
    priority: int = Field(0, ge=0, le=1000)
    frequency_cap: Optional[int] = Field(None, ge=0)
    is_active: bool = True
    audience: str = "all"

    @field_validator("placement")
    @classmethod
    def _valid_placement(cls, v: str) -> str:
        if v not in PLACEMENTS:
            raise ValueError(f"placement inválido. Use uno de: {', '.join(PLACEMENTS)}")
        return v

    @field_validator("template_type")
    @classmethod
    def _valid_template(cls, v: str) -> str:
        if v not in TEMPLATES:
            raise ValueError(f"template_type inválido. Use uno de: {', '.join(TEMPLATES)}")
        return v

    @model_validator(mode="after")
    def _check_dates(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at debe ser posterior a starts_at")
        return self


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=160)
    message: Optional[str] = Field(None, min_length=1)
    placement: Optional[str] = None
    template_type: Optional[str] = None
    background_image_url: Optional[str] = None
    media_public_id: Optional[str] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    duration_seconds: Optional[int] = Field(None, ge=1, le=120)
    priority: Optional[int] = Field(None, ge=0, le=1000)
    frequency_cap: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    audience: Optional[str] = None

    @field_validator("placement")
    @classmethod
    def _valid_placement(cls, v):
        if v is not None and v not in PLACEMENTS:
            raise ValueError(f"placement inválido. Use uno de: {', '.join(PLACEMENTS)}")
        return v

    @field_validator("template_type")
    @classmethod
    def _valid_template(cls, v):
        if v is not None and v not in TEMPLATES:
            raise ValueError(f"template_type inválido. Use uno de: {', '.join(TEMPLATES)}")
        return v


class AnnouncementResponse(AnnouncementBase):
    id: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    status: str = "inactive"  # active | scheduled | expired | inactive (calculado)

    class Config:
        from_attributes = True


class AnnouncementPublic(BaseModel):
    """Vista pública para la app móvil. No expone campos internos."""

    id: int
    title: str
    message: str
    placement: str
    template_type: str
    background_image_url: Optional[str] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    duration_seconds: int
    priority: int

    class Config:
        from_attributes = True
