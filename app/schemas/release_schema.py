"""
PROXVEL Backend - App Release Schemas (6B).
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

PLATFORMS = ("android", "ios")


class ReleaseUpdate(BaseModel):
    """Actualización de metadata (no del binario)."""
    version_name: Optional[str] = Field(None, min_length=1, max_length=40)
    version_code: Optional[int] = Field(None, ge=1)
    platform: Optional[str] = None
    changelog: Optional[str] = None


class ReleasePublishUpdate(BaseModel):
    is_published: bool


class ReleaseResponse(BaseModel):
    """Vista admin: incluye metadata interna."""
    id: int
    version_name: str
    version_code: int
    platform: str
    apk_url: Optional[str] = None
    file_public_id: Optional[str] = None
    file_size: Optional[int] = None
    changelog: Optional[str] = None
    is_published: bool
    published_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReleasePublic(BaseModel):
    """Vista pública (landing): sin campos internos (file_public_id, created_by)."""
    version_name: str
    version_code: int
    platform: str
    apk_url: Optional[str] = None
    file_size: Optional[int] = None
    changelog: Optional[str] = None
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True
