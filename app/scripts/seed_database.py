"""
PROXVEL Backend - Seeder Script.
Carga los 5 CSV desde app/data hacia PostgreSQL.
Fase 2B.
"""

import logging
import sys
from pathlib import Path

# Configurar path para imports
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from app.config.settings import get_settings
from app.config.database import SessionLocal
from app.repositories.csv_loader import load_all_csvs, get_data
from app.utils.normalizers import generate_destination_id, safe_float, safe_int
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.aspect_score_model import DestinationAspectScore
from app.models.climate_score_model import ClimateScore
from app.models.crowd_score_model import CrowdScore
from app.models.contextual_ranking_model import ContextualRanking

# Logging config
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger("seeder")

def run_seeder():
    settings = get_settings()
    if not settings.DATABASE_URL:
        logger.error("No DATABASE_URL configured.")
        return

    # 1. Cargar CSV a memoria
    logger.info("Cargando CSV desde disco...")
    load_all_csvs(settings.data_path)

    data_absa = get_data("absa") or []
    data_clima = get_data("clima") or []
    data_aforo = get_data("aforo") or []
    data_ranking = get_data("ranking") or []
    data_catalog = get_data("catalog") or []

    if not all([data_absa, data_clima, data_aforo, data_ranking, data_catalog]):
        logger.error("Faltan archivos CSV, revisa la carpeta app/data")
        return

    # 2. Conectar a BD
    db = SessionLocal()
    try:
        # Borrado controlado de tablas metodológicas (Reverse dependency order)
        logger.info("Limpiando tablas metodológicas (Borrado Controlado)...")
        db.execute(delete(ContextualRanking))
        db.execute(delete(CrowdScore))
        db.execute(delete(ClimateScore))
        db.execute(delete(DestinationAspectScore))
        db.execute(delete(TourismCatalog))
        db.commit()

        # 3. Insertar Destinos (Upsert idempotent)
        logger.info("Procesando destinations...")
        destinations_map = {}
        
        # Extraer destinos únicos de todos los CSV
        for row in data_catalog:
            dest_id = row.get("destination_id") or generate_destination_id(row.get("destination", ""))
            destinations_map[dest_id] = row.get("destination", "Unknown")
            
        for dataset in [data_absa, data_clima, data_aforo, data_ranking]:
            for row in dataset:
                name = row.get("destination")
                if name:
                    dest_id = generate_destination_id(name)
                    if dest_id not in destinations_map:
                        destinations_map[dest_id] = name

        for dest_id, dest_name in destinations_map.items():
            stmt = insert(Destination).values(
                destination_id=dest_id,
                destination=dest_name
            ).on_conflict_do_nothing(index_elements=["destination_id"])
            db.execute(stmt)
        db.commit()

        # 4. Insertar Tourism Catalog
        logger.info("Procesando tourism_catalog...")
        for row in data_catalog:
            dest_id = row.get("destination_id") or generate_destination_id(row.get("destination", ""))
            db.add(TourismCatalog(
                destination_id=dest_id,
                official_name=row.get("official_name"),
                department=row.get("department"),
                province=row.get("province"),
                district=row.get("district"),
                city=row.get("city"),
                region=row.get("region"),
                category=row.get("category"),
                type_=row.get("type"),
                subtype=row.get("subtype"),
                hierarchy=safe_int(row.get("hierarchy")),
                altitude_m=safe_int(row.get("altitude_m")),
                description=row.get("description"),
                experience_type=row.get("experience_type"),
                visitor_info_summary=row.get("visitor_info_summary"),
                activities_summary=row.get("activities_summary"),
                accessibility_summary=row.get("accessibility_summary"),
                latitude=safe_float(row.get("latitude")),
                longitude=safe_float(row.get("longitude")),
                geofence_radius_m=safe_float(row.get("geofence_radius_m")),
                cover_image_url=row.get("cover_image_url"),
                gallery_image_1=row.get("gallery_image_1"),
                gallery_image_2=row.get("gallery_image_2"),
                gallery_image_3=row.get("gallery_image_3"),
                gallery_image_4=row.get("gallery_image_4"),
                image_source=row.get("image_source"),
                image_license_note=row.get("image_license_note"),
                official_source_name=row.get("official_source_name"),
                official_source_code=row.get("official_source_code"),
                official_source_url=row.get("official_source_url"),
                secondary_source_name=row.get("secondary_source_name"),
                secondary_source_code=row.get("secondary_source_code"),
                secondary_source_url=row.get("secondary_source_url"),
                map_source=row.get("map_source"),
                data_status=row.get("data_status"),
            ))
        db.commit()

        # 5. Insertar ABSA
        logger.info("Procesando destination_aspect_scores...")
        for row in data_absa:
            dest_id = generate_destination_id(row.get("destination", ""))
            db.add(DestinationAspectScore(
                destination_id=dest_id,
                accesibilidad=safe_float(row.get("accesibilidad")),
                aforo_multitudes=safe_float(row.get("aforo_multitudes")),
                alojamiento=safe_float(row.get("alojamiento")),
                atencion_servicio=safe_float(row.get("atencion_servicio")),
                atractivos=safe_float(row.get("atractivos")),
                clima=safe_float(row.get("clima")),
                costos=safe_float(row.get("costos")),
                gastronomia=safe_float(row.get("gastronomia")),
                limpieza=safe_float(row.get("limpieza")),
                seguridad=safe_float(row.get("seguridad")),
            ))
        db.commit()

        # 6. Insertar Climate Scores (Fase4_V2: score_clima→score_clima_modelo, clima_categoria→nivel_clima)
        logger.info("Procesando climate_scores...")
        for row in data_clima:
            dest_id = generate_destination_id(row.get("destination", ""))
            db.add(ClimateScore(
                destination_id=dest_id,
                month=safe_int(row.get("month"), default=1),
                temp_prom=safe_float(row.get("temp_prom")),
                pp=safe_float(row.get("pp")),
                clima_categoria=row.get("nivel_clima"),
                score_clima=safe_float(row.get("score_clima_modelo")),
            ))
        db.commit()

        # 7. Insertar Crowd Scores (Fase4_V2: periodo columna eliminada)
        logger.info("Procesando crowd_scores...")
        for row in data_aforo:
            dest_id = generate_destination_id(row.get("destination", ""))
            db.add(CrowdScore(
                destination_id=dest_id,
                year=safe_int(row.get("year"), default=2024),
                month=safe_int(row.get("month"), default=1),
                visitantes_mes=safe_float(row.get("visitantes_mes")),
                aforo_normalizado=safe_float(row.get("aforo_normalizado")),
                nivel_aforo=row.get("nivel_aforo"),
                score_aforo_base=safe_float(row.get("score_aforo_base")),
                periodo=None,
            ))
        db.commit()

        # 8. Insertar Contextual Rankings (Fase4_V2: rank→nueva_posicion, compatibilidad_final→compatibilidad_contextual_pct)
        logger.info("Procesando contextual_rankings...")
        # Batch insert for performance as there are 9000 rows
        rankings = []
        for row in data_ranking:
            dest_id = generate_destination_id(row.get("destination", ""))
            rankings.append(ContextualRanking(
                user_id=row.get("user_id"),
                destination_id=dest_id,
                rank=safe_int(row.get("nueva_posicion")),
                score_final_fase4=safe_float(row.get("score_final_fase4")),
                compatibilidad_final=safe_float(row.get("compatibilidad_contextual_pct")),
                etiqueta_final=row.get("etiqueta_final"),
                explicacion_final=row.get("explicacion_final"),
            ))
        db.bulk_save_objects(rankings)
        db.commit()

        logger.info("¡Seeding completado exitosamente!")

    except Exception as e:
        logger.error("Error durante el seeding: %s", e)
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_seeder()
