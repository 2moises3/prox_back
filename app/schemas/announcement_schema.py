"""
PROXVEL Backend - Announcement Schemas.
Validación y serialización de anuncios internos.
"""

import re
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator

# Valores permitidos (alineados con el dashboard y la app)
PLACEMENTS = ("app_start", "home_top", "destination_detail", "global_modal")
TEMPLATES = (
    "image_banner",
    "gradient_card",
    "minimal_notice",
    "tourism_highlight",
    "maintenance_notice",
)

# Pantallas de la app a las que puede llevar el botón del anuncio.
APP_SCREENS = ("/search", "/favorites", "/map", "/notifications", "/profile/preferences")
_DESTINATION_ROUTE = re.compile(r"^/destination/[a-z0-9_]+$")

EventType = Literal["impression", "click", "dismiss"]


def _to_utc_naive(v: Optional[datetime]) -> Optional[datetime]:
    """Las fechas se guardan en UTC sin zona. Una fecha con zona se convierte a UTC."""
    if v is not None and v.tzinfo is not None:
        return v.astimezone(timezone.utc).replace(tzinfo=None)
    return v


def _clean_text(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    return v or None


def validate_cta_url(v: Optional[str]) -> Optional[str]:
    v = _clean_text(v)
    if v is None:
        return None
    if v in APP_SCREENS or _DESTINATION_ROUTE.match(v):
        return v
    if v.startswith("https://") and len(v) > len("https://") + 3:
        return v
    raise ValueError(
        "La acción del botón debe ser un destino (/destination/<id>), una pantalla de la app "
        f"({', '.join(APP_SCREENS)}) o un enlace https://"
    )


class AnnouncementBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=160)
    message: str = Field(..., min_length=1, max_length=600)
    placement: str = "app_start"
    template_type: str = "gradient_card"
    background_image_url: Optional[str] = None
    media_public_id: Optional[str] = None
    cta_text: Optional[str] = Field(None, max_length=40)
    cta_url: Optional[str] = None
    target_destination_id: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    duration_seconds: int = Field(5, ge=3, le=60)
    priority: int = Field(0, ge=0, le=1000)
    frequency_cap: Optional[int] = Field(1, ge=0, le=100)
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

    @field_validator("cta_url")
    @classmethod
    def _valid_cta(cls, v):
        return validate_cta_url(v)

    @field_validator("cta_text", "target_destination_id")
    @classmethod
    def _strip(cls, v):
        return _clean_text(v)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def _utc(cls, v):
        return _to_utc_naive(v)

    @model_validator(mode="after")
    def _check(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at debe ser posterior a starts_at")
        if bool(self.cta_text) != bool(self.cta_url):
            raise ValueError("El botón necesita texto y acción (o deja ambos vacíos).")
        if self.placement != "destination_detail":
            self.target_destination_id = None
        return self


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=160)
    message: Optional[str] = Field(None, min_length=1, max_length=600)
    placement: Optional[str] = None
    template_type: Optional[str] = None
    background_image_url: Optional[str] = None
    media_public_id: Optional[str] = None
    cta_text: Optional[str] = Field(None, max_length=40)
    cta_url: Optional[str] = None
    target_destination_id: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    duration_seconds: Optional[int] = Field(None, ge=3, le=60)
    priority: Optional[int] = Field(None, ge=0, le=1000)
    frequency_cap: Optional[int] = Field(None, ge=0, le=100)
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

    @field_validator("cta_url")
    @classmethod
    def _valid_cta(cls, v):
        return validate_cta_url(v)

    @field_validator("cta_text", "target_destination_id")
    @classmethod
    def _strip(cls, v):
        return _clean_text(v)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def _utc(cls, v):
        return _to_utc_naive(v)


def _iso_utc(v: Optional[datetime]) -> Optional[str]:
    """Serializa en ISO con 'Z' para que el dashboard no la confunda con hora local."""
    if v is None:
        return None
    if v.tzinfo is not None:
        v = v.astimezone(timezone.utc).replace(tzinfo=None)
    return v.isoformat(timespec="seconds") + "Z"


class AnnouncementResponse(AnnouncementBase):
    id: int
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    status: str = "inactive"  # active | scheduled | expired | inactive (calculado)
    impressions: int = 0
    clicks: int = 0
    dismissals: int = 0
    target_destination_name: Optional[str] = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def _check(self):  # la respuesta refleja lo guardado; no se re-valida la coherencia
        return self

    @field_serializer("starts_at", "ends_at", "created_at", "updated_at")
    def _ser_dates(self, v):
        return _iso_utc(v)


class AnnouncementPublic(BaseModel):
    """Vista pública para la app móvil. No expone campos internos ni métricas."""

    id: int
    title: str
    message: str
    placement: str
    template_type: str
    background_image_url: Optional[str] = None
    cta_text: Optional[str] = None
    cta_url: Optional[str] = None
    target_destination_id: Optional[str] = None
    duration_seconds: int
    priority: int
    frequency_cap: Optional[int] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("updated_at")
    def _ser_updated(self, v):
        return _iso_utc(v)


class AnnouncementEvent(BaseModel):
    event: EventType
