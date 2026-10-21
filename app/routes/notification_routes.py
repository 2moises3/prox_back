"""
PROXVEL Backend - Notification Routes.
Centro de notificaciones de la app móvil (campana del Home).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.security import get_current_user
from app.schemas.user_schema import UserResponse
from app.schemas.notification_schema import NotificationPreferencesUpdate
from app.services import notification_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/notifications", tags=["Notificaciones"])


@router.get("", summary="Lista unificada de notificaciones (anuncios + avisos personales)")
def list_notifications(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    data = notification_service.feed(db, current_user.user_id, limit=limit, offset=offset)
    return success_response(data=data, message="Notificaciones obtenidas correctamente")


@router.get("/unread-count", summary="Cantidad de notificaciones sin leer (para el punto de la campana)")
def unread_count(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    count = notification_service.unread_count(db, current_user.user_id)
    return success_response(data={"unread_count": count}, message="Conteo obtenido")


@router.get("/preferences", summary="Preferencias del centro de notificaciones")
def get_preferences(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    return success_response(data=notification_service.preferences(db, current_user.user_id))


@router.patch("/preferences", summary="Configurar avisos visibles dentro de la app")
def patch_preferences(
    payload: NotificationPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    data = notification_service.update_preferences(
        db, current_user.user_id, payload.model_dump(exclude_unset=True, exclude_none=True))
    return success_response(data=data)


@router.post("/read-all", summary="Marcar todas como leídas")
def read_all(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    count = notification_service.mark_all_read(db, current_user.user_id)
    return success_response(data={"marked": count}, message="Notificaciones marcadas como leídas")


@router.get("/{item_id}", summary="Consultar un aviso disponible para la cuenta")
def get_notification(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    item = notification_service.get_item(db, current_user.user_id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Este aviso ya no está disponible")
    return success_response(data=item)


@router.post("/{item_id}/read", summary="Marcar una notificación como leída (n-<id> o a-<id>)")
def read_one(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    if not notification_service.mark_read(db, current_user.user_id, item_id):
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return success_response(data={"id": item_id}, message="Notificación marcada como leída")
