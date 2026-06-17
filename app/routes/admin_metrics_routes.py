"""
PROXVEL Backend - Admin Metrics Routes.
Overview de métricas reales para el dashboard administrativo.
Protegido con require_admin_or_super_admin.
"""

from fastapi import APIRouter, Depends
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
