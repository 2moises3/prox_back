"""
PROXVEL Backend - Public Announcement Routes.
Endpoint público para que la app móvil consuma anuncios activos.
Solo expone anuncios activos, dentro de rango de fechas y ordenados por prioridad.
NO expone campos internos (created_by, frequency_cap, audience, fechas internas).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.services import announcement_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/announcements", tags=["Anuncios (público)"])


@router.get("/active", summary="Anuncios activos para la app móvil")
def get_active_announcements(
    placement: str | None = Query(
        None,
        description="Filtrar por ubicación: app_start | home_top | destination_detail | global_modal",
    ),
    db: Session = Depends(get_db),
):
    items = announcement_service.list_public_active(db, placement=placement)
    return success_response(
        data=[i.model_dump() for i in items],
        message="Anuncios activos obtenidos correctamente",
    )
