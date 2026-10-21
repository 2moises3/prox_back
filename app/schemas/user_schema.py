"""
PROXVEL Backend - User Schemas.
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class UserBase(BaseModel):
    name: Optional[str] = None
    email: str
    residence_department: Optional[str] = Field(None, max_length=120)
    residence_province: Optional[str] = Field(None, max_length=120)
    residence_city: Optional[str] = Field(None, max_length=120)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Mínimo 8 caracteres")
    # Aceptación de Términos y Política de Privacidad, y declaración de ser mayor de 18 años.
    accepted_terms: bool = False

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    residence_department: Optional[str] = Field(None, max_length=120)
    residence_province: Optional[str] = Field(None, max_length=120)
    residence_city: Optional[str] = Field(None, max_length=120)

class UserResponse(UserBase):
    user_id: str
    role: str
    is_active: bool
    avatar_url: Optional[str] = None
    accepted_terms_version: Optional[str] = None
    accepted_terms_at: Optional[datetime] = None
    # Uso interno (validación de sesiones); exclude=True evita que salga en las respuestas.
    password_changed_at: Optional[datetime] = Field(None, exclude=True)

    class Config:
        from_attributes = True


# ── Gestión administrativa de usuarios (6B) ──────────────────────────────────

ALLOWED_ROLES = ("traveler", "admin", "super_admin")
DASHBOARD_CREATABLE_ROLES = ("traveler", "admin")


class AdminUserCreate(BaseModel):
    """Payload para crear usuario desde el dashboard (super_admin only)."""
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=8, description="Mínimo 8 caracteres")
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
    residence_department: Optional[str] = None
    residence_province: Optional[str] = None
    residence_city: Optional[str] = None
    created_at: datetime
    account_status: str
    deletion_requested_at: Optional[datetime] = None
    deletion_scheduled_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    deletion_reason: Optional[str] = None
    deletion_requested_by: Optional[str] = None

    class Config:
        from_attributes = True
