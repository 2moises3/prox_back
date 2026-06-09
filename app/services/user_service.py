"""
PROXVEL Backend - User Service.
"""
from typing import List, Optional
from app.repositories import db_user_repository
from app.schemas.user_schema import UserResponse

def get_demo_users() -> List[UserResponse]:
    users = db_user_repository.get_demo_users()
    return [UserResponse.model_validate(u) for u in users]

def get_user_by_id(user_id: str) -> Optional[UserResponse]:
    user = db_user_repository.get_user_by_id(user_id)
    if user:
        return UserResponse.model_validate(user)
    return None
