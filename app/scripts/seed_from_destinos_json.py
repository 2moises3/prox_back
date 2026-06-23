"""
Seed desde destinos.json → BD.
- Crea los destinos nuevos como is_active=False.
- Destinos que ya existen: actualiza sus puntajes ABSA.
- Ejecutar: python -m app.scripts.seed_from_destinos_json
"""
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.config.database import SessionLocal
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.aspect_score_model import DestinationAspectScore
from app.utils.normalizers import generate_destination_id

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "destinos.json"

_ABSA_ASPECTS = [
    "accesibilidad", "aforo_multitudes", "alojamiento", "atencion_servicio",
    "atractivos", "clima", "costos", "gastronomia", "limpieza", "seguridad",
]


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    destinos = data["destinos"]
    db = SessionLocal()

    created = updated_absa = skipped = 0

    try:
        for name, info in destinos.items():
            dest_id = generate_destination_id(name)

            dest = db.query(Destination).filter_by(destination_id=dest_id).first()
            if not dest:
                # Busca por nombre exacto (por si el ID difiere)
                dest = db.query(Destination).filter_by(destination=name).first()

            if not dest:
                dest = Destination(
                    destination_id=dest_id,
                    destination=name,
                    is_active=False,
                )
                db.add(dest)
                db.flush()

                db.add(TourismCatalog(destination_id=dest_id))
                print(f"  [NUEVO]       {name}  →  {dest_id}  (inactivo)")
                created += 1
            else:
                print(f"  [EXISTENTE]   {name}  →  {dest.destination_id}")
                skipped += 1

            # Upsert ABSA scores
            absa = info.get("absa", {})
            scores = db.query(DestinationAspectScore).filter_by(
                destination_id=dest.destination_id
            ).first()

            if not scores:
                scores = DestinationAspectScore(destination_id=dest.destination_id)
                db.add(scores)

            for asp in _ABSA_ASPECTS:
                if asp in absa:
                    setattr(scores, asp, float(absa[asp]))

            updated_absa += 1

        db.commit()
        print(f"\n✅ Seed completado — nuevos: {created}, ABSA actualizados: {updated_absa}, ya existían: {skipped}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
