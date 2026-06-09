"""
PROXVEL Backend - Data Status Service.
Verifica el estado de carga de los archivos CSV y la disponibilidad de PostgreSQL.
"""

import logging
from sqlalchemy import text
from app.repositories.csv_loader import get_all_status, is_loaded
from app.config.database import SessionLocal
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.aspect_score_model import DestinationAspectScore
from app.models.climate_score_model import ClimateScore
from app.models.crowd_score_model import CrowdScore
from app.models.contextual_ranking_model import ContextualRanking

logger = logging.getLogger(__name__)


def check_data_status() -> dict:
    """
    Devuelve el estado de carga combinado: PostgreSQL + CSV fallback.
    """
    csv_status = get_all_status()
    files_loaded = sum(1 for v in csv_status.values() if v)
    
    db_connected = False
    tables_available = False
    counts = {}
    
    try:
        db = SessionLocal()
        try:
            # Check connection
            db.execute(text("SELECT 1"))
            db_connected = True
            
            # Check counts
            counts = {
                "destinations": db.query(Destination).count(),
                "tourism_catalog": db.query(TourismCatalog).count(),
                "destination_aspect_scores": db.query(DestinationAspectScore).count(),
                "climate_scores": db.query(ClimateScore).count(),
                "crowd_scores": db.query(CrowdScore).count(),
                "contextual_rankings": db.query(ContextualRanking).count(),
            }
            if counts["destinations"] > 0:
                tables_available = True
                
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Error checking database status: {e}")
        pass

    data_mode = "database" if (db_connected and tables_available) else "csv_fallback"

    response = {
        "success": True,
        "data": {
            "data_mode": data_mode,
            "csv_status": {
                "loaded": files_loaded > 0,
                "files_loaded": files_loaded
            },
            "database_status": {
                "connected": db_connected,
            },
            "fallback_available": files_loaded > 0
        }
    }
    
    if db_connected:
        response["data"]["database_status"]["tables_available"] = tables_available
        response["data"]["database_status"]["counts"] = counts

    return response


def is_data_available(key: str) -> bool:
    """Verifica si un CSV específico está disponible."""
    return is_loaded(key)
