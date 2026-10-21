"""
PROXVEL Backend - FastAPI Application.
Punto de entrada principal de la aplicación.
Registra routers, configura CORS. Fuente de datos: PostgreSQL.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config.cors import configure_cors
from app.core.audit import install_audit_handler, purge_audit
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
    admin_engine_routes,
    notification_routes,
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
    install_audit_handler()
    job = asyncio.create_task(_daily_jobs(settings)) if settings.ENABLE_BACKGROUND_JOBS else None
    logger.info("Backend listo (fuente de datos: PostgreSQL).")
    yield
    if job:
        job.cancel()
    logger.info("Backend detenido.")


async def _daily_jobs(settings) -> None:
    """Cada 24 h: ejecuta las eliminaciones de cuenta vencidas y borra auditoría antigua."""
    from app.services.user_admin_service import process_due_deletions

    await asyncio.sleep(300)  # deja arrancar y estabilizar el servicio
    while True:
        try:
            result, error, _ = await asyncio.to_thread(process_due_deletions)
            if not error and result.get("processed"):
                logger.info("Eliminaciones de cuenta procesadas: %s", result["processed"])
            purged = await asyncio.to_thread(purge_audit, settings.AUDIT_RETENTION_DAYS)
            if purged:
                logger.info("Auditoría: %s eventos antiguos borrados", purged)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # una falla no debe detener las siguientes ejecuciones
            logger.error("Tarea diaria falló: %s", exc)
        await asyncio.sleep(24 * 3600)


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
        # Swagger solo en desarrollo (o con ENABLE_DOCS=true): no se expone la API en producción.
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    # Configurar CORS
    configure_cors(app)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if settings.is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """
        Los clientes (app y dashboard) muestran `detail` como texto: se devuelve un mensaje
        legible en vez de la lista técnica de Pydantic (que además revela el esquema interno).
        """
        errors = exc.errors()
        first = errors[0] if errors else {}
        field = str(first.get("loc", ("",))[-1]) if first.get("loc") else ""
        kind = first.get("type", "")
        if field in ("password", "new_password") and kind == "string_too_short":
            message = "La contraseña debe tener al menos 8 caracteres."
        elif field == "code":
            message = "El código debe tener 6 dígitos."
        elif kind == "missing":
            message = f"Falta el campo obligatorio: {field}."
        elif field == "email" or "email" in kind:
            message = "Ingresa un correo electrónico válido."
        else:
            message = "Revisa los datos enviados e intenta nuevamente."
        return JSONResponse(status_code=422, content={"detail": message})

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
    app.include_router(admin_engine_routes.router, prefix=api_prefix)
    app.include_router(notification_routes.router, prefix=api_prefix)
    app.include_router(release_public_routes.router, prefix=api_prefix)

    return app


# Instancia global de la app
app = create_app()
