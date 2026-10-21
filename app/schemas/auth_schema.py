"""
PROXVEL Backend - Auth Schemas.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from app.schemas.user_schema import UserResponse

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, description="Mínimo 8 caracteres")

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., pattern=r"^\d{6}$", description="Código de 6 dígitos recibido por correo")
    new_password: str = Field(..., min_length=8, description="Mínimo 8 caracteres")

class TokenData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
