"""
PROXVEL Backend - Public Announcement Routes.
Endpoints públicos para que la app móvil consuma anuncios activos y reporte vistas/clics.
Solo expone anuncios activos, dentro de rango de fechas y ordenados por prioridad.
NO expone campos internos (created_by, audience, métricas).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.rate_limit import announcement_events, client_ip
from app.schemas.announcement_schema import AnnouncementEvent
from app.services import announcement_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/announcements", tags=["Anuncios (público)"])

# Límite de eventos por IP: holgado para uso normal, corta el spam de métricas.
_EVENTS_PER_MINUTE = 120


@router.get("/active", summary="Anuncios activos para la app móvil")
def get_active_announcements(
    placement: str | None = Query(
        None,
        description="Filtrar por ubicación: app_start | home_top | destination_detail | global_modal",
    ),
    destination_id: str | None = Query(
        None, description="Para destination_detail: solo anuncios de ese destino o generales.",
    ),
    db: Session = Depends(get_db),
):
    items = announcement_service.list_public_active(db, placement=placement, destination_id=destination_id)
    return success_response(
        data=[i.model_dump(mode="json") for i in items],
        message="Anuncios activos obtenidos correctamente",
    )


@router.post("/{announcement_id}/events", summary="Registrar vista, clic o cierre de un anuncio")
def post_announcement_event(
    announcement_id: int,
    payload: AnnouncementEvent,
    request: Request,
    db: Session = Depends(get_db),
):
    key = f"ann_events:{client_ip(request)}"
    if announcement_events.count(key, 60) >= _EVENTS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Demasiados eventos. Intenta más tarde.")
    announcement_events.hit(key, 60)
    if not announcement_service.record_event(db, announcement_id, payload.event):
        raise HTTPException(status_code=404, detail="Anuncio no encontrado")
    return success_response(data=None, message="Evento registrado")
