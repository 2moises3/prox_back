"""
PROXVEL Backend - User Schemas.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class UserBase(BaseModel):
    name: Optional[str] = None
    email: str

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)
    avatar_url: Optional[str] = None

class UserResponse(UserBase):
    user_id: str
    role: str
    is_active: bool
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


# ── Gestión administrativa de usuarios (6B) ──────────────────────────────────

ALLOWED_ROLES = ("traveler", "admin", "super_admin")
DASHBOARD_CREATABLE_ROLES = ("traveler", "admin")


class AdminUserCreate(BaseModel):
    """Payload para crear usuario desde el dashboard (super_admin only)."""
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)
    role: str  # Validado contra DASHBOARD_CREATABLE_ROLES en el servicio


class AdminRoleUpdate(BaseModel):
    role: str


class AdminStatusUpdate(BaseModel):
    is_active: bool


class AdminUserResponse(BaseModel):
    """Vista admin de un usuario (incluye created_at). Nunca password_hash."""
    user_id: str
    name: Optional[str] = None
    email: str
    role: str
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: datetime
    account_status: str
    deletion_requested_at: Optional[datetime] = None
    deletion_scheduled_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    deletion_reason: Optional[str] = None
    deletion_requested_by: Optional[str] = None

    class Config:
        from_attributes = True
