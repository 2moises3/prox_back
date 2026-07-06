"""
PROXVEL Backend - Configuración centralizada.
Carga variables desde .env con pydantic-settings.

NOTA: SECRET_KEY es obligatorio. Si no está definido en .env,
el backend no arrancará. Rotar SECRET_KEY invalida todas las
sesiones activas (tokens JWT) y fuerza re-login de todos los usuarios.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración global del backend."""

    APP_NAME: str = "PROXVEL Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000


    # CORS - orígenes permitidos (separados por coma en .env)
    CORS_ORIGINS: str = "*"

    # URL de conexión a la base de datos PostgreSQL
    DATABASE_URL: str | None = None

    # JWT Config
    SECRET_KEY: str  # Obligatorio — definir en .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200 # 30 dias para pruebas locales

    # Cloudinary Config
    CLOUDINARY_CLOUD_NAME: str | None = None
    CLOUDINARY_API_KEY: str | None = None
    CLOUDINARY_API_SECRET: str | None = None
    CLOUDINARY_FOLDER: str = "proxvel/destinations"
    MAX_UPLOAD_SIZE_MB: int = 5



    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Singleton cacheado de Settings."""
    return Settings()
