"""
PROXVEL Backend - Health Routes.
Endpoint de verificación de estado del servicio.
"""

from fastapi import APIRouter

from app.config.settings import get_settings

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Estado del servicio",
    description="Verifica que el backend esté activo y responde.",
)
def health_check():
    """Devuelve el estado actual del backend."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
