"""
PROXVEL Backend - Configuración centralizada.
Carga variables desde .env con pydantic-settings.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuración global del backend."""

    APP_NAME: str = "PROXVEL Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Directorio de datos CSV (relativo a la raíz del proyecto)
    DATA_DIR: str = "app/data"

    # CORS - orígenes permitidos (separados por coma en .env)
    CORS_ORIGINS: str = "*"

    # URL de conexión a la base de datos PostgreSQL
    DATABASE_URL: str | None = None

    # JWT Config
    SECRET_KEY: str = "proxvel_super_secret_key_for_jwt_auth_local_only"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200 # 30 dias para pruebas locales

    @property
    def data_path(self) -> Path:
        """Devuelve la ruta absoluta al directorio de datos CSV."""
        return Path(__file__).resolve().parent.parent.parent / self.DATA_DIR

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Singleton cacheado de Settings."""
    return Settings()
