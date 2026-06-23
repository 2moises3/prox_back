"""
Seed completo del motor V1 desde destinos.json → BD.
Llena: engine_config, destinations (+ABSA), destination_tags, destination_month_context.
Idempotente: se puede correr varias veces sin duplicar.

Ejecutar: python -m app.scripts.seed_engine_v1
"""
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.config.database import SessionLocal
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.aspect_score_model import DestinationAspectScore
from app.models.engine_config_model import EngineConfig
from app.models.destination_tag_model import DestinationTag
from app.models.destination_month_context_model import DestinationMonthContext
from app.utils.normalizers import generate_destination_id
from app.services.destination_metric_sync_service import recalculate_status

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "destinos.json"

_ABSA_ASPECTS = [
    "accesibilidad", "aforo_multitudes", "alojamiento", "atencion_servicio",
    "atractivos", "clima", "costos", "gastronomia", "limpieza", "seguridad",
]


def _seed_config(db, config: dict):
    cfg = db.query(EngineConfig).first()
    if not cfg:
        cfg = EngineConfig()
        db.add(cfg)
    ftol = config.get("factor_tolerancia", {})
    cfg.alpha_afinidad = float(config.get("alpha_afinidad", 0.85))
    cfg.beta_intereses = float(config.get("beta_intereses", 0.15))
    cfg.beta_contexto = float(config.get("beta_contexto", 0.30))
    cfg.w_clima = float(config.get("w_clima", 0.5))
    cfg.w_aforo = float(config.get("w_aforo", 0.5))
    cfg.factor_tolerancia_baja = float(ftol.get("baja", 1.0))
    cfg.factor_tolerancia_media = float(ftol.get("media", 0.65))
    cfg.factor_tolerancia_alta = float(ftol.get("alta", 0.35))


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    config = data["config"]
    destinos = data["destinos"]
    db = SessionLocal()

    created = absa_n = tags_n = months_n = 0

    try:
        _seed_config(db, config)

        for name, info in destinos.items():
            dest_id = generate_destination_id(name)

            dest = db.query(Destination).filter_by(destination_id=dest_id).first()
            if not dest:
                dest = db.query(Destination).filter_by(destination=name).first()
            if not dest:
                dest = Destination(destination_id=dest_id, destination=name, is_active=False)
                db.add(dest)
                db.flush()
                db.add(TourismCatalog(destination_id=dest_id))
                created += 1
                print(f"  [NUEVO]     {name}  (inactivo)")
            else:
                dest_id = dest.destination_id

            # ── ABSA ──
            absa = info.get("absa", {})
            scores = db.query(DestinationAspectScore).filter_by(destination_id=dest_id).first()
            if not scores:
                scores = DestinationAspectScore(destination_id=dest_id)
                db.add(scores)
            for asp in _ABSA_ASPECTS:
                if asp in absa:
                    setattr(scores, asp, float(absa[asp]))
            absa_n += 1

            # ── Tags (reemplaza) ──
            db.query(DestinationTag).filter_by(destination_id=dest_id).delete()
            for tag in info.get("tags_interes", []):
                db.add(DestinationTag(destination_id=dest_id, tag=str(tag).strip().lower()))
                tags_n += 1

            # ── Contexto mensual (reemplaza) ──
            db.query(DestinationMonthContext).filter_by(destination_id=dest_id).delete()
            for mkey, m in info.get("meses", {}).items():
                db.add(DestinationMonthContext(
                    destination_id=dest_id,
                    month=int(mkey),
                    clima_score=m.get("clima_score"),
                    clima_nivel=m.get("clima_nivel"),
                    temp_prom=m.get("temp_prom"),
                    pp=m.get("pp"),
                    aforo_score=m.get("aforo_score"),
                    aforo_nivel=m.get("aforo_nivel"),
                    aforo_fuente=m.get("aforo_fuente"),
                ))
                months_n += 1

        db.commit()

        # Recalcular data_status para todos los destinos procesados
        for name, info in destinos.items():
            dest_id = generate_destination_id(name)
            dest = db.query(Destination).filter_by(destination_id=dest_id).first()
            if not dest:
                dest = db.query(Destination).filter_by(destination=name).first()
            if dest:
                recalculate_status(db, dest.destination_id)
        db.commit()

        print(f"\n[OK] Seed motor V1 completado:")
        print(f"   destinos nuevos : {created}")
        print(f"   ABSA            : {absa_n}")
        print(f"   tags            : {tags_n}")
        print(f"   contexto meses  : {months_n}")
        print(f"   engine_config   : 1 registro")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
