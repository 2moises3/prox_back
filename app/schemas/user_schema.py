"""
PROXVEL Backend - User Schemas.
"""
from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: str
    role: str

class UserResponse(UserBase):
    is_active: bool

    class Config:
        from_attributes = True
