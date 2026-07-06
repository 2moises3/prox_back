"""
PROXVEL Backend - Reset Seeded Tables.
Limpia únicamente las 6 tablas metodológicas cargadas por el seeder.
"""

import logging
import sys
from pathlib import Path

# Configurar path para imports
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import delete

from app.config.database import SessionLocal
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.aspect_score_model import DestinationAspectScore
from app.models.climate_score_model import ClimateScore
from app.models.crowd_score_model import CrowdScore
from app.models.contextual_ranking_model import ContextualRanking

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger("reset")

def reset_tables():
    db = SessionLocal()
    try:
        logger.info("Borrando ContextualRanking...")
        db.execute(delete(ContextualRanking))
        logger.info("Borrando CrowdScore...")
        db.execute(delete(CrowdScore))
        logger.info("Borrando ClimateScore...")
        db.execute(delete(ClimateScore))
        logger.info("Borrando DestinationAspectScore...")
        db.execute(delete(DestinationAspectScore))
        logger.info("Borrando TourismCatalog...")
        db.execute(delete(TourismCatalog))
        logger.info("Borrando Destination...")
        # NOTA: destinations solo se puede borrar si NO hay FK de tablas operativas.
        # En Fase 2B, como users/reviews están vacías, esto no fallará.
        db.execute(delete(Destination))
        
        db.commit()
        logger.info("Tablas reseteadas exitosamente.")
    except Exception as e:
        logger.error("Error reseteando tablas: %s", e)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_tables()
