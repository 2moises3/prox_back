"""
PROXVEL Backend - Data Routes.
Endpoint para verificar el estado de carga de los archivos CSV.
"""

from fastapi import APIRouter

from app.services import data_status_service

router = APIRouter(prefix="/data", tags=["Data"])


@router.get(
    "/status",
    summary="Estado de carga de CSV y Base de Datos",
    description=(
        "Indica el modo de operación actual (database o csv_fallback) "
        "y el estado de conexión y tablas de PostgreSQL."
    ),
)
def data_status():
    """Devuelve el estado combinado de DB y CSV."""
    status = data_status_service.check_data_status()
    return status
