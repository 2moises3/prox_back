"""
PROXVEL Backend - Review Routes.
"""
import logging

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import List

from app.services import review_service
from app.schemas.review_schema import ReviewCreate, ReviewResponse
from app.utils.response_builder import success_response
from app.core.security import get_current_user, require_admin_or_super_admin
from app.schemas.user_schema import UserResponse

router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED, summary="Crear nueva reseña")
def create_review(review: ReviewCreate, current_user: UserResponse = Depends(get_current_user)):
    # Sobrescribimos o forzamos el user_id para evitar suplantación
    review.user_id = current_user.user_id
    
    created_review, error = review_service.create_review(review)
    if error:
        if "no existe" in error:
            raise HTTPException(status_code=404, detail=error)
        raise HTTPException(status_code=422, detail=error)
    return success_response(data=created_review.model_dump(), message="Reseña registrada correctamente")

@router.get("/pending", response_model=dict, summary="Obtener reseñas pendientes")
def get_pending_reviews(_: UserResponse = Depends(require_admin_or_super_admin)):
    reviews = review_service.get_pending_reviews()
    return success_response(data=[r.model_dump() for r in reviews], message="Reseñas pendientes obtenidas")

@router.get("/destination/{destination_id}", response_model=dict, summary="Obtener reseñas por destino")
def get_reviews_by_destination(destination_id: str, current_user: UserResponse = Depends(get_current_user)):
    is_admin = current_user.role in ("admin", "super_admin")
    reviews = review_service.get_reviews_by_destination(destination_id, include_hidden=is_admin)
    # Autor visible: nombre y la inicial del apellido ("Lucía P."), nunca el correo.
    from sqlalchemy import func
    from app.config.database import SessionLocal
    from app.models.user_model import User
    from app.models.review_report_model import ReviewReport
    ids = {r.user_id for r in reviews}
    rids = [r.review_id for r in reviews]
    with SessionLocal() as db:
        nombres = dict(db.query(User.user_id, User.name).filter(User.user_id.in_(ids)).all()) if ids else {}
        reportes = dict(db.query(ReviewReport.review_id, func.count(ReviewReport.id))
                        .filter(ReviewReport.review_id.in_(rids)).group_by(ReviewReport.review_id).all()) if (is_admin and rids) else {}
    data = []
    for r in reviews:
        row = {**r.model_dump(), "author_name": _short_name(nombres.get(r.user_id)),
               "is_own": r.user_id == current_user.user_id}
        if is_admin:
            row["report_count"] = int(reportes.get(r.review_id, 0))
        else:
            row.pop("user_id", None)  # el identificador interno solo lo ve el equipo
            row.pop("status", None)
        data.append(row)
    return success_response(data=data, message="Reseñas de destino obtenidas")


def _short_name(full: str | None) -> str | None:
    parts = (full or "").split()
    if not parts or parts[0].lower() in ("usuario", "viajero"):
        return None
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[1][0].upper()}."

@router.get("/user/{user_id}", response_model=dict, summary="Obtener reseñas por usuario")
def get_reviews_by_user(user_id: str, current_user: UserResponse = Depends(get_current_user)):
    if current_user.user_id != user_id:
        raise HTTPException(status_code=403, detail="No tienes permiso para ver las reseñas de este usuario")
        
    reviews = review_service.get_reviews_by_user(user_id)
    # Nombre del destino para que la app no muestre el identificador interno.
    from app.config.database import SessionLocal
    from app.models.destination_model import Destination
    ids = {r.destination_id for r in reviews if r.destination_id}
    with SessionLocal() as db:
        nombres = dict(db.query(Destination.destination_id, Destination.destination)
                       .filter(Destination.destination_id.in_(ids)).all()) if ids else {}
    data = [{**r.model_dump(), "destination_name": nombres.get(r.destination_id)} for r in reviews]
    return success_response(data=data, message="Reseñas de usuario obtenidas")

@router.get("/{review_id}", response_model=dict, summary="Obtener reseña por ID")
def get_review_by_id(review_id: str, current_user: UserResponse = Depends(get_current_user)):
    review = review_service.get_review_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Reseña no encontrada")
    if review.user_id != current_user.user_id and current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="No tienes permiso para ver esta reseña")
    return success_response(data=review.model_dump(), message="Reseña obtenida")


# ── Reportes y moderación ────────────────────────────────────────────────────

REPORT_REASONS = ("ofensiva", "falsa", "spam", "datos_personales", "otro")


class ReviewReportRequest(BaseModel):
    reason: str


@router.post("/{review_id}/report", response_model=dict, summary="Reportar una reseña")
def report_review(review_id: str, payload: ReviewReportRequest, current_user: UserResponse = Depends(get_current_user)):
    if payload.reason not in REPORT_REASONS:
        raise HTTPException(status_code=422, detail=f"Motivo no válido. Usa: {', '.join(REPORT_REASONS)}.")
    from app.config.database import SessionLocal
    from app.models.review_model import Review
    from app.models.review_report_model import ReviewReport
    with SessionLocal() as db:
        review = db.query(Review).filter(Review.review_id == review_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Reseña no encontrada")
        if review.user_id == current_user.user_id:
            raise HTTPException(status_code=409, detail="No puedes reportar tu propia reseña.")
        exists = db.query(ReviewReport).filter_by(review_id=review_id, reporter_user_id=current_user.user_id).first()
        if not exists:
            db.add(ReviewReport(review_id=review_id, reporter_user_id=current_user.user_id, reason=payload.reason))
            db.commit()
    return success_response(data=None, message="Gracias. Revisaremos la reseña.")


class ReviewHiddenRequest(BaseModel):
    hidden: bool


@router.patch("/{review_id}/hidden", response_model=dict, summary="Ocultar o mostrar una reseña (equipo)")
def set_review_hidden(review_id: str, payload: ReviewHiddenRequest,
                      current_user: UserResponse = Depends(require_admin_or_super_admin)):
    from app.config.database import SessionLocal
    from app.models.review_model import Review
    with SessionLocal() as db:
        review = db.query(Review).filter(Review.review_id == review_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Reseña no encontrada")
        review.is_hidden = payload.hidden
        db.commit()
    logging.getLogger("proxvel.audit").info("AUDIT review_hidden user=%s review=%s hidden=%s",
                                            current_user.user_id, review_id, payload.hidden)
    return success_response(data={"review_id": review_id, "hidden": payload.hidden},
                            message="Reseña oculta" if payload.hidden else "Reseña visible")
