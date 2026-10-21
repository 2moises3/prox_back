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

        # En desarrollo, admitir orígenes locales habituales (4000, 5173, 3000) y regex para Flutter Web
        if settings.DEBUG:
            for dev_origin in (
                "http://localhost:4000",
                "http://127.0.0.1:4000",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ):
                if dev_origin not in allow_origins:
                    allow_origins.append(dev_origin)

        allow_origin_regex = (
            r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$" if settings.DEBUG else None
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_origin_regex=allow_origin_regex,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
