"""
PROXVEL Backend - Configuración CORS.
Permite conexión futura desde Flutter y otros clientes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings


def configure_cors(app: FastAPI) -> None:
    """Configura el middleware CORS en la aplicación."""
    settings = get_settings()

    origins = settings.CORS_ORIGINS
    allow_origins = origins.split(",") if origins != "*" else ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
