"""
PROXVEL Backend - Check Database Counts Script.
Verifica los conteos de las tablas en PostgreSQL.
"""

import logging
import sys
from pathlib import Path

# Configurar path para imports
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.config.database import SessionLocal
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.aspect_score_model import DestinationAspectScore
from app.models.climate_score_model import ClimateScore
from app.models.crowd_score_model import CrowdScore
from app.models.contextual_ranking_model import ContextualRanking
from app.models.user_model import User
from app.models.traveler_profile_model import TravelerProfile
from app.models.favorite_model import Favorite
from app.models.review_model import Review
from app.models.review_aspect_rating_model import ReviewAspectRating
from app.models.monthly_review_batch_model import MonthlyReviewBatch
from app.models.model_update_run_model import ModelUpdateRun
from app.models.visit_model import Visit

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger("checker")

def check_counts():
    db = SessionLocal()
    if not db:
        logger.error("Database is not configured.")
        return

    try:
        counts = {
            "Metodológicas": {
                "destinations": db.query(Destination).count(),
                "tourism_catalog": db.query(TourismCatalog).count(),
                "destination_aspect_scores": db.query(DestinationAspectScore).count(),
                "climate_scores": db.query(ClimateScore).count(),
                "crowd_scores": db.query(CrowdScore).count(),
                "contextual_rankings": db.query(ContextualRanking).count(),
            },
            "Operativas (Deberían ser 0)": {
                "users": db.query(User).count(),
                "traveler_profiles": db.query(TravelerProfile).count(),
                "favorites": db.query(Favorite).count(),
                "reviews": db.query(Review).count(),
                "review_aspect_ratings": db.query(ReviewAspectRating).count(),
                "monthly_review_batches": db.query(MonthlyReviewBatch).count(),
                "model_update_runs": db.query(ModelUpdateRun).count(),
                "visits": db.query(Visit).count(),
            }
        }

        logger.info("=== RESULTADOS DE CONTEO EN POSTGRESQL ===")
        for category, tables in counts.items():
            logger.info(f"--- Tablas {category} ---")
            for table, count in tables.items():
                logger.info(f"{table.ljust(30)}: {count}")

    except Exception as e:
        logger.error("Error al contar las tablas: %s", e)
    finally:
        db.close()

if __name__ == "__main__":
    check_counts()
