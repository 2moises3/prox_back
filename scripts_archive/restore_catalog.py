import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.config.database import SessionLocal
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.repositories.csv_loader import get_data, load_all_csvs
from app.utils.normalizers import generate_destination_id, safe_float, safe_int
from app.config.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger("restore_catalog")

def main():
    settings = get_settings()
    load_all_csvs(settings.data_path)
    data_catalog = get_data("catalog") or []
    
    if not data_catalog:
        logger.error("No se encontró data del catálogo.")
        return

    db = SessionLocal()
    try:
        # 1. Update existing destinations or create new ones
        for row in data_catalog:
            dest_id = row.get("destination_id") or generate_destination_id(row.get("destination", ""))
            dest_name = row.get("destination")
            
            existing_dest = db.query(Destination).filter(Destination.destination_id == dest_id).first()
            if existing_dest:
                logger.info(f"Actualizando destino existente: {dest_id} -> {dest_name}")
                existing_dest.destination = dest_name
            else:
                logger.info(f"Creando nuevo destino: {dest_id} -> {dest_name}")
                new_dest = Destination(destination_id=dest_id, destination=dest_name)
                db.add(new_dest)
        db.commit()
        
        # 2. Update existing tourism_catalog or create new ones
        for row in data_catalog:
            dest_id = row.get("destination_id") or generate_destination_id(row.get("destination", ""))
            
            existing_cat = db.query(TourismCatalog).filter(TourismCatalog.destination_id == dest_id).first()
            
            if existing_cat:
                logger.info(f"Actualizando catálogo para: {dest_id}")
                # Update attributes
                existing_cat.official_name = row.get("official_name")
                existing_cat.department = row.get("department")
                existing_cat.province = row.get("province")
                existing_cat.district = row.get("district")
                existing_cat.city = row.get("city")
                existing_cat.region = row.get("region")
                existing_cat.category = row.get("category")
                existing_cat.type_ = row.get("type")
                existing_cat.subtype = row.get("subtype")
                existing_cat.hierarchy = safe_int(row.get("hierarchy"))
                existing_cat.altitude_m = safe_int(row.get("altitude_m"))
                existing_cat.description = row.get("description")
                existing_cat.experience_type = row.get("experience_type")
                existing_cat.visitor_info_summary = row.get("visitor_info_summary")
                existing_cat.activities_summary = row.get("activities_summary")
                existing_cat.accessibility_summary = row.get("accessibility_summary")
                existing_cat.latitude = safe_float(row.get("latitude"))
                existing_cat.longitude = safe_float(row.get("longitude"))
                existing_cat.geofence_radius_m = safe_float(row.get("geofence_radius_m"))
                existing_cat.cover_image_url = row.get("cover_image_url")
                existing_cat.gallery_image_1 = row.get("gallery_image_1")
                existing_cat.gallery_image_2 = row.get("gallery_image_2")
                existing_cat.gallery_image_3 = row.get("gallery_image_3")
                existing_cat.gallery_image_4 = row.get("gallery_image_4")
                existing_cat.image_source = row.get("image_source")
                existing_cat.image_license_note = row.get("image_license_note")
                existing_cat.official_source_name = row.get("official_source_name")
                existing_cat.official_source_code = row.get("official_source_code")
                existing_cat.official_source_url = row.get("official_source_url")
                existing_cat.secondary_source_name = row.get("secondary_source_name")
                existing_cat.secondary_source_code = row.get("secondary_source_code")
                existing_cat.secondary_source_url = row.get("secondary_source_url")
                existing_cat.map_source = row.get("map_source")
                existing_cat.data_status = row.get("data_status")
            else:
                logger.info(f"Creando nuevo catálogo para: {dest_id}")
                new_cat = TourismCatalog(
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
                )
                db.add(new_cat)
        db.commit()
        logger.info("Restauración de catálogo completada con éxito.")

        # Print state
        dests = db.query(Destination).all()
        print("--- DESTINATIONS AFTER UPDATE ---")
        for d in dests:
            print(f"{d.destination_id} | {d.destination}")

    except Exception as e:
        logger.error(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
