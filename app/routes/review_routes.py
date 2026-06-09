"""
PROXVEL Backend - Review Routes.
"""
from fastapi import APIRouter, HTTPException, status
from typing import List

from app.services import review_service
from app.schemas.review_schema import ReviewCreate, ReviewResponse
from app.utils.response_builder import success_response

router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED, summary="Crear nueva reseña")
def create_review(review: ReviewCreate):
    created_review, error = review_service.create_review(review)
    if error:
        if "no existe" in error:
            raise HTTPException(status_code=404, detail=error)
        raise HTTPException(status_code=422, detail=error)
    return success_response(data=created_review.model_dump(), message="Reseña registrada correctamente")

@router.get("/pending", response_model=dict, summary="Obtener reseñas pendientes")
def get_pending_reviews():
    reviews = review_service.get_pending_reviews()
    return success_response(data=[r.model_dump() for r in reviews], message="Reseñas pendientes obtenidas")

@router.get("/destination/{destination_id}", response_model=dict, summary="Obtener reseñas por destino")
def get_reviews_by_destination(destination_id: str):
    reviews = review_service.get_reviews_by_destination(destination_id)
    return success_response(data=[r.model_dump() for r in reviews], message="Reseñas de destino obtenidas")

@router.get("/user/{user_id}", response_model=dict, summary="Obtener reseñas por usuario")
def get_reviews_by_user(user_id: str):
    reviews = review_service.get_reviews_by_user(user_id)
    return success_response(data=[r.model_dump() for r in reviews], message="Reseñas de usuario obtenidas")

@router.get("/{review_id}", response_model=dict, summary="Obtener reseña por ID")
def get_review_by_id(review_id: str):
    review = review_service.get_review_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")
    return success_response(data=review.model_dump(), message="Reseña obtenida")
