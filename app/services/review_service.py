"""
PROXVEL Backend - Review Service.
"""
from typing import List, Optional, Tuple
from app.repositories import db_review_repository
from app.repositories import db_user_repository
from app.repositories import db_destination_repository
from app.schemas.review_schema import ReviewCreate, ReviewResponse

VALID_ASPECTS = {
    "atractivos", "costos", "seguridad", "accesibilidad", "alojamiento",
    "atencion_servicio", "limpieza", "gastronomia", "clima", "aforo_multitudes"
}

def validate_review(review_data: ReviewCreate) -> Tuple[bool, Optional[str]]:
    # Validate user exists
    user = db_user_repository.get_user_by_id(review_data.user_id)
    if not user:
        return False, "Usuario no existe"
        
    # Validate destination exists
    destination = db_destination_repository.get_destination_by_id(review_data.destination_id)
    if not destination:
        return False, "Destino no existe"
        
    # Validate aspects
    for ar in review_data.aspect_ratings:
        if ar.aspect not in VALID_ASPECTS:
            return False, f"Aspecto inválido: {ar.aspect}"
            
    return True, None

def create_review(review_data: ReviewCreate) -> Tuple[Optional[ReviewResponse], Optional[str]]:
    is_valid, error = validate_review(review_data)
    if not is_valid:
        return None, error
        
    review = db_review_repository.create_review(review_data)
    if review:
        return ReviewResponse.model_validate(review), None
    return None, "Error interno al crear reseña"

def get_review_by_id(review_id: str) -> Optional[ReviewResponse]:
    review = db_review_repository.get_review_by_id(review_id)
    if review:
        return ReviewResponse.model_validate(review)
    return None

def get_reviews_by_destination(destination_id: str, include_hidden: bool = False) -> List[ReviewResponse]:
    reviews = db_review_repository.get_reviews_by_destination(destination_id, include_hidden=include_hidden)
    return [ReviewResponse.model_validate(r) for r in reviews]

def get_reviews_by_user(user_id: str) -> List[ReviewResponse]:
    reviews = db_review_repository.get_reviews_by_user(user_id)
    return [ReviewResponse.model_validate(r) for r in reviews]

def get_pending_reviews() -> List[ReviewResponse]:
    reviews = db_review_repository.get_pending_reviews()
    return [ReviewResponse.model_validate(r) for r in reviews]
