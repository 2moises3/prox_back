"""
PROXVEL Backend - Data Status Service.
Verifica la disponibilidad de PostgreSQL (fuente única de datos).
"""

import logging
from sqlalchemy import text
from app.config.database import SessionLocal
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.aspect_score_model import DestinationAspectScore
from app.models.destination_tag_model import DestinationTag
from app.models.destination_month_context_model import DestinationMonthContext
from app.models.engine_config_model import EngineConfig

logger = logging.getLogger(__name__)


def check_data_status() -> dict:
    """Devuelve el estado de PostgreSQL: conexión, tablas y conteos del motor."""
    db_connected = False
    tables_available = False
    counts = {}

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            db_connected = True

            counts = {
                "destinations": db.query(Destination).count(),
                "tourism_catalog": db.query(TourismCatalog).count(),
                "destination_aspect_scores": db.query(DestinationAspectScore).count(),
                "destination_tags": db.query(DestinationTag).count(),
                "destination_month_context": db.query(DestinationMonthContext).count(),
                "engine_config": db.query(EngineConfig).count(),
            }
            if counts["destinations"] > 0:
                tables_available = True
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Error checking database status: {e}")

    response = {
        "success": True,
        "data": {
            "data_mode": "database_and_thesis_v3",
                "engine": {"source": "tesis_v3", "version": "tesis-v3-20261022", "scientific_data": "validated_snapshot", "read_only": True},
            "database_status": {
                "connected": db_connected,
            },
        },
    }

    if db_connected:
        response["data"]["database_status"]["tables_available"] = tables_available
        response["data"]["database_status"]["counts"] = counts

    return response
