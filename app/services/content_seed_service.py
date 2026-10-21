"""
Carga de la ficha comercial de los destinos desde `seed_data/destination_content.json`.

Sirve para dejar una base recién creada con datos listos (descripción, coordenadas, cómo llegar, etc.)
sin tener que escribirlos a mano en el dashboard. No toca puntajes del motor ni opiniones.
"""
import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.tourism_catalog_model import TourismCatalog

logger = logging.getLogger("proxvel.audit")

CONTENT_FILE = Path(__file__).resolve().parent.parent.parent / "seed_data" / "destination_content.json"

# Campos de la ficha que este archivo puede llenar.
CONTENT_FIELDS = (
    "city", "category", "altitude_m", "latitude", "longitude", "description",
    "activities_summary", "visitor_info_summary", "accessibility_summary",
    "recommended_duration", "how_to_get", "difficulty", "official_website",
)


def load_content_file() -> dict[str, dict]:
    """Lee el archivo y devuelve {destination_id: campos}. Lanza FileNotFoundError si no existe."""
    data = json.loads(CONTENT_FILE.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_") and isinstance(v, dict)}


def load_content(db: Session, overwrite: bool = False) -> dict:
    """
    Llena la ficha comercial de los destinos del archivo.

    - overwrite=False (por defecto): solo completa campos vacíos; lo editado a mano no se toca.
    - overwrite=True: reemplaza los valores existentes por los del archivo.
    """
    content = load_content_file()
    catalogs = {c.destination_id: c for c in db.query(TourismCatalog).all()}

    filled = 0
    updated_destinations: list[str] = []
    missing: list[str] = []

    for destination_id, fields in content.items():
        catalog = catalogs.get(destination_id)
        if catalog is None:
            missing.append(destination_id)
            continue
        changed = 0
        for field in CONTENT_FIELDS:
            value = fields.get(field)
            if value is None:
                continue
            current = getattr(catalog, field, None)
            if current == value:
                continue
            if current is None or (isinstance(current, str) and not current.strip()) or overwrite:
                setattr(catalog, field, value)
                changed += 1
        if changed:
            filled += changed
            updated_destinations.append(destination_id)

    db.commit()
    return {
        "overwrite": overwrite,
        "destinations_in_file": len(content),
        "destinations_updated": len(updated_destinations),
        "fields_written": filled,
        "missing_in_database": missing,
    }
