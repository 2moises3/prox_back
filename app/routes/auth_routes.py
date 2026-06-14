"""
PROXVEL Backend - Auth Routes.
"""
from fastapi import APIRouter, HTTPException, status, Depends

from app.schemas.auth_schema import LoginRequest, TokenData
from app.schemas.user_schema import UserResponse
from app.repositories import db_user_repository
from app.utils.hash_util import verify_password
from app.core.security import create_access_token, get_current_user
from app.utils.response_builder import success_response

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login", response_model=dict, summary="Autenticar usuario y obtener JWT")
def login(request: LoginRequest):
    # Buscar usuario
    user = db_user_repository.get_user_by_email(request.email)
    if not user:
        # User not found (return generic error for security)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    
    # Verificar contraseña
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas"
        )
    
    # Usuario válido, crear payload
    user_response = UserResponse.model_validate(user)
    token_payload = {
        "sub": user.user_id,
        "email": user.email
    }
    
    # Crear token
    access_token = create_access_token(data=token_payload)
    
    return success_response(
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_response.model_dump()
        },
        message="Login correcto"
    )

@router.get("/me", response_model=dict, summary="Obtener usuario autenticado actualmente")
def get_me(current_user: UserResponse = Depends(get_current_user)):
    return success_response(
        data=current_user.model_dump(),
        message="Usuario autenticado"
    )
