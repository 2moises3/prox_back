"""
PROXVEL Backend - Configuración CORS.
Permite conexión desde el dashboard web y otros clientes autorizados.

Reglas:
- Si CORS_ORIGINS == "*", se usa wildcard SIN credenciales (spec HTTP).
- Si CORS_ORIGINS es una lista explícita, se usa CON credenciales (JWT).
- Flutter móvil no depende de CORS; el dashboard web sí.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings


def configure_cors(app: FastAPI) -> None:
    """Configura el middleware CORS en la aplicación."""
    settings = get_settings()

    origins = settings.CORS_ORIGINS

    if origins == "*":
        # Wildcard: NO se puede combinar con allow_credentials=True
        # según la especificación HTTP (los navegadores lo rechazan).
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        # Lista explícita de orígenes: seguro con credenciales.
        allow_origins = [o.strip() for o in origins.split(",") if o.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
