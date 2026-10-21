"""
PROXVEL Backend - Admin Metrics Routes.
Overview de métricas reales para el dashboard administrativo.
Protegido con require_admin_or_super_admin.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.core.security import require_admin_or_super_admin
from app.schemas.user_schema import UserResponse
from app.services import admin_metrics_service
from app.utils.response_builder import success_response

router = APIRouter(prefix="/admin/metrics", tags=["Admin - Métricas"])


@router.get("/overview", summary="Resumen de métricas reales del dashboard")
def metrics_overview(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    data = admin_metrics_service.get_overview(db)
    return success_response(data=data, message="Métricas obtenidas correctamente")


@router.get("/charts", summary="Datos formateados para gráficos")
def metrics_charts(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    data = admin_metrics_service.get_charts_data(db)
    return success_response(data=data, message="Datos de gráficos obtenidos correctamente")


@router.get("/activity", summary="Actividad reciente real (registros, reseñas, fotos, anuncios, versiones)")
def metrics_activity(
    limit: int = Query(8, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    return success_response(data=admin_metrics_service.get_activity(db, limit), message="Actividad reciente")


@router.get("/priorities", summary="Pendientes reales para el inicio del dashboard")
def metrics_priorities(
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(require_admin_or_super_admin),
):
    return success_response(data=admin_metrics_service.get_priorities(db), message="Prioridades")
