"""
PROXVEL Backend - User Schemas.
"""

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

class UserResponse(UserBase):
    user_id: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True
