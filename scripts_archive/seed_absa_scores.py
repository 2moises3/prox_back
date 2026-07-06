"""
Seed de puntajes ABSA desde CSV a PostgreSQL.

Lee matriz_absa_normalizada.csv y puebla destination_aspect_scores.
Corre una sola vez después de un despliegue inicial o cuando quieras
reinicializar los puntajes de los 3 destinos originales.

Uso (dentro del contenedor o con el venv activo):
    python -m app.scripts.seed_absa_scores
"""

import logging
import sys
from pathlib import Path

# Permite ejecutar como módulo o directamente
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sqlalchemy import select

from app.config.database import SessionLocal
from app.config.settings import get_settings
from app.models.aspect_score_model import DestinationAspectScore
from app.repositories.csv_loader import load_csv
from app.utils.normalizers import generate_destination_id, safe_float

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

ABSA_ASPECTS = [
    "accesibilidad", "aforo_multitudes", "alojamiento", "atencion_servicio",
    "atractivos", "clima", "costos", "gastronomia", "limpieza", "seguridad",
]


def seed_absa_scores() -> None:
    settings = get_settings()
    absa_path = settings.data_path / "matriz_absa_normalizada.csv"
    rows = load_csv(absa_path)

    if not rows:
        logger.error("No se encontró o no se pudo leer: %s", absa_path)
        sys.exit(1)

    db = SessionLocal()
    try:
        inserted = updated = 0
        for row in rows:
            name = row.get("destination", "")
            if not name:
                continue

            destination_id = generate_destination_id(name)
            scores = {a: safe_float(row.get(a), 0.5) for a in ABSA_ASPECTS}

            existing = db.scalar(
                select(DestinationAspectScore).where(
                    DestinationAspectScore.destination_id == destination_id
                )
            )
            if existing:
                for k, v in scores.items():
                    setattr(existing, k, v)
                updated += 1
                logger.info("Actualizado: %s", destination_id)
            else:
                db.add(DestinationAspectScore(destination_id=destination_id, **scores))
                inserted += 1
                logger.info("Insertado:   %s", destination_id)

        db.commit()
        logger.info("Seed completado — insertados: %d, actualizados: %d", inserted, updated)
    except Exception as e:
        db.rollback()
        logger.error("Error durante el seed: %s", e)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_absa_scores()
