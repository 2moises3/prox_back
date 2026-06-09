"""
PROXVEL Backend - Database Config.
Configuración de conexión a PostgreSQL usando SQLAlchemy.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.settings import get_settings

settings = get_settings()

if settings.DATABASE_URL:
    # Crear engine sincrónico para PostgreSQL
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,  # Mostrar logs SQL si está en modo DEBUG
        pool_pre_ping=True,   # Verificar si la conexión está viva antes de usarla
    )

    # Crear factoría de sesiones
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine = None
    SessionLocal = None


def get_db():
    """Dependency para inyectar la sesión de base de datos en los endpoints."""
    if SessionLocal is None:
        raise RuntimeError("Database is not configured. Missing DATABASE_URL.")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
