"""
PROXVEL Backend - FastAPI Application.
Punto de entrada principal de la aplicación.
Registra routers, configura CORS. Fuente de datos: PostgreSQL.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.cors import configure_cors
from app.config.settings import get_settings
from app.routes import (
    data_routes,
    destination_routes,
    health_routes,
    recommendation_routes,
    tourism_routes,
    user_routes,
    review_routes,
    admin_training_routes,
    auth_routes,
    favorite_routes,
    archive_routes,
    destination_media_routes,
    admin_metrics_routes,
    admin_announcement_routes,
    announcement_public_routes,
    admin_destination_routes,
    admin_user_routes,
    admin_release_routes,
    release_public_routes,
    admin_import_routes,
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Evento de ciclo de vida de FastAPI.
    El backend lee 100% desde PostgreSQL; no carga archivos al arrancar.
    """
    settings = get_settings()
    logger.info("Iniciando %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("Backend listo (fuente de datos: PostgreSQL).")
    yield
    logger.info("Backend detenido.")


def create_app() -> FastAPI:
    """Crea y configura la aplicación FastAPI."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "API REST para el sistema de recomendación turística PROXVEL. "
            "Expone datos generados por las fases metodológicas de la tesis: "
            "ABSA (Fase 2), Afinidad destino-perfil (Fase 3) y "
            "Re-ranking contextual (Fase 4). Incluye catálogo turístico "
            "oficial complementario (MINCETUR)."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configurar CORS
    configure_cors(app)

    # Registrar routers bajo /api/v1
    api_prefix = "/api/v1"
    app.include_router(health_routes.router, prefix=api_prefix)
    app.include_router(data_routes.router, prefix=api_prefix)
    app.include_router(destination_routes.router, prefix=api_prefix)
    app.include_router(recommendation_routes.router, prefix=api_prefix)
    app.include_router(tourism_routes.router, prefix=api_prefix)
    app.include_router(user_routes.router, prefix=api_prefix)
    app.include_router(auth_routes.router, prefix=api_prefix)
    app.include_router(review_routes.router, prefix=api_prefix)
    app.include_router(admin_training_routes.router, prefix=api_prefix)
    app.include_router(favorite_routes.router, prefix=api_prefix)
    app.include_router(archive_routes.router, prefix=api_prefix)
    app.include_router(destination_media_routes.router, prefix=api_prefix)
    app.include_router(admin_metrics_routes.router, prefix=api_prefix)
    app.include_router(admin_announcement_routes.router, prefix=api_prefix)
    app.include_router(announcement_public_routes.router, prefix=api_prefix)
    app.include_router(admin_destination_routes.router, prefix=api_prefix)
    app.include_router(admin_user_routes.router, prefix=api_prefix)
    app.include_router(admin_release_routes.router, prefix=api_prefix)
    app.include_router(admin_import_routes.router, prefix=api_prefix)
    app.include_router(release_public_routes.router, prefix=api_prefix)

    return app


# Instancia global de la app
app = create_app()
