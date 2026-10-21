from app.core.legal import TERMS_VERSION
"""
PROXVEL Backend - User Service.
"""
from typing import List, Optional
from app.repositories import db_user_repository
from app.schemas.user_schema import UserResponse, UserCreate, UserUpdate
from app.utils.hash_util import get_password_hash

def get_demo_users() -> List[UserResponse]:
    users = db_user_repository.get_demo_users()
    return [UserResponse.model_validate(u) for u in users]

def get_user_by_id(user_id: str) -> Optional[UserResponse]:
    user = db_user_repository.get_user_by_id(user_id)
    if user:
        return UserResponse.model_validate(user)
    return None

def create_user(user_data: UserCreate) -> tuple[Optional[UserResponse], Optional[str]]:
    existing_user = db_user_repository.get_user_by_email(user_data.email)
    if existing_user:
        return None, "El correo electrónico ya está registrado"
        
    new_user_id = db_user_repository.get_next_user_id()
    hashed_password = get_password_hash(user_data.password)
    
    user = db_user_repository.create_user(
        user_id=new_user_id,
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password,
        accepted_terms_version=TERMS_VERSION if user_data.accepted_terms else None,
    )
    if user:
        return UserResponse.model_validate(user), None
    return None, "Error interno al crear el usuario"

def update_user(user_id: str, user_data: UserUpdate) -> tuple[Optional[UserResponse], Optional[str]]:
    update_dict = user_data.model_dump(exclude_unset=True)
    
    if "email" in update_dict:
        existing_user = db_user_repository.get_user_by_email(update_dict["email"])
        if existing_user and existing_user.user_id != user_id:
            return None, "El correo electrónico ya está registrado por otro usuario"
            
    user = db_user_repository.update_user(user_id, update_dict)
    if user:
        return UserResponse.model_validate(user), None
    return None, "Usuario no encontrado o error interno"
