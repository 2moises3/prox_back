"""
PROXVEL Backend - Configuración centralizada.
Carga variables desde .env con pydantic-settings.

NOTA: SECRET_KEY es obligatorio. Si no está definido en .env,
el backend no arrancará. Rotar SECRET_KEY invalida todas las
sesiones activas (tokens JWT) y fuerza re-login de todos los usuarios.

Con APP_ENV=production el backend se niega a arrancar si la configuración
es insegura (CORS abierto, DEBUG activo, SECRET_KEY débil o sin base de datos).
"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings

_WEAK_SECRETS = {"changeme", "change-me", "secret", "secretkey", "supersecret", "dev", "development", "test"}


class Settings(BaseSettings):
    """Configuración global del backend."""

    APP_NAME: str = "PROXVEL Backend"
    APP_VERSION: str = "1.0.0"
    # development | production. En production se activan las validaciones estrictas.
    APP_ENV: str = "development"
    # Recarga automática y modo desarrollo. Debe ser False en producción.
    DEBUG: bool = False
    # Muestra las consultas SQL en el log (independiente de DEBUG).
    SQL_ECHO: bool = False
    # Swagger (/docs, /redoc). En production solo si ENABLE_DOCS=true.
    ENABLE_DOCS: bool | None = None
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ACCOUNT_DELETION_GRACE_DAYS: int = 14
    # Registros de seguridad (IP, accesos, contraseñas): días que se conservan antes de borrarse.
    AUDIT_RETENTION_DAYS: int = 90
    # Tareas diarias (eliminaciones vencidas y purga de auditoría). Desactivar solo en pruebas.
    ENABLE_BACKGROUND_JOBS: bool = True

    # CORS - orígenes permitidos (separados por coma en .env). Nunca "*" en producción.
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173"
    )

    # Detrás de un proxy (Railway, nginx) la IP real llega en X-Forwarded-For.
    # Activar solo si el backend NO es accesible directamente desde internet.
    TRUST_PROXY_HEADERS: bool = False

    # URL de conexión a la base de datos PostgreSQL
    DATABASE_URL: str | None = None

    # JWT Config
    SECRET_KEY: str  # Obligatorio — definir en .env
    ALGORITHM: str = "HS256"
    # Duración del token del viajero (app móvil, sin refresh token): 14 días.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 20160
    # Duración del token de admin / super_admin (dashboard web): 8 horas.
    ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # Límite de intentos (ver app/core/rate_limit.py)
    LOGIN_MAX_FAILURES: int = 5            # fallos por correo+IP antes de bloquear
    LOGIN_MAX_FAILURES_PER_IP: int = 30    # fallos por IP (cualquier correo)
    LOGIN_WINDOW_SECONDS: int = 900        # ventana de 15 minutos
    REGISTER_MAX_PER_IP: int = 10          # registros por IP y hora

    # Correo (recuperar contraseña). console = solo log (desarrollo); smtp = envío real.
    EMAIL_BACKEND: str = "console"
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    SMTP_USE_TLS: bool = True
    # Correo de soporte que se muestra en la app si el código no llega.
    SUPPORT_EMAIL: str | None = None

    # Recuperar contraseña
    # Recuperar contraseña por correo (código de 6 dígitos). Apagado en la v1: mientras tanto
    # la app muestra el correo de soporte y un super_admin entrega una contraseña temporal.
    PASSWORD_RESET_BY_EMAIL: bool = False
    PASSWORD_RESET_CODE_MINUTES: int = 15
    PASSWORD_RESET_MAX_ATTEMPTS: int = 5    # intentos con un código antes de invalidarlo
    PASSWORD_RESET_PER_EMAIL: int = 3       # solicitudes de código por correo y hora
    PASSWORD_RESET_PER_IP: int = 10         # solicitudes de código por IP y hora

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

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.strip().lower() == "production"

    @property
    def docs_enabled(self) -> bool:
        if self.ENABLE_DOCS is not None:
            return self.ENABLE_DOCS
        return not self.is_production

    @model_validator(mode="after")
    def _validate_environment(self):
        if len(self.SECRET_KEY) < 16:
            raise ValueError("SECRET_KEY debe tener al menos 16 caracteres.")
        if not self.is_production:
            return self

        problems = []
        origins = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        if not origins or "*" in origins:
            problems.append("CORS_ORIGINS no puede ser '*' ni estar vacío en producción")
        if self.DEBUG:
            problems.append("DEBUG debe ser False en producción")
        if len(self.SECRET_KEY) < 32 or self.SECRET_KEY.strip().lower() in _WEAK_SECRETS:
            problems.append("SECRET_KEY debe tener al menos 32 caracteres y no ser un valor de ejemplo")
        if not self.DATABASE_URL:
            problems.append("DATABASE_URL es obligatorio")
        if self.PASSWORD_RESET_BY_EMAIL and (
            self.EMAIL_BACKEND.strip().lower() != "smtp" or not self.SMTP_HOST or not self.SMTP_FROM
        ):
            problems.append("recuperar contraseña necesita EMAIL_BACKEND=smtp con SMTP_HOST y SMTP_FROM")
        if problems:
            raise ValueError("Configuración insegura para APP_ENV=production: " + "; ".join(problems) + ".")
        return self


@lru_cache()
def get_settings() -> Settings:
    """Singleton cacheado de Settings."""
    return Settings()
