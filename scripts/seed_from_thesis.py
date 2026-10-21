"""
PROXVEL - Seed del motor de recomendación desde los CSV de la tesis (Fases 3 y 4).

Fuentes (proxvel_backend/seed_data/):
  registro_maestro_centros_turisticos.csv   -> destinations, tourism_catalog, destination_tags
  destination_content.json                  -> ficha comercial (descripcion, coordenadas de Google Maps, etc.)
  matriz_destino_aspecto_sentimiento.csv    -> destination_aspect_scores (ABSA, 8 aspectos core)
  clima_scores.csv                          -> destination_month_context (clima)
  aforo_scores.csv                          -> destination_month_context (aforo) + engine_config

Idempotente (upsert por destination_id / mes). No borra nada.
Marca los 14 destinos como in_engine=True (los que la tesis entrenó y validó).

Uso (desde proxvel_backend, dentro del contenedor):
    python scripts/seed_from_thesis.py            # aplica
    python scripts/seed_from_thesis.py --dry-run  # solo muestra el resumen
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import app.models  # noqa: F401  (registra todos los modelos en el mapper)
import app.models.archive_model  # noqa: F401
from app.config.database import SessionLocal
from app.models.aspect_score_model import DestinationAspectScore
from app.models.destination_model import Destination
from app.models.destination_month_context_model import DestinationMonthContext
from app.models.destination_tag_model import DestinationTag
from app.models.engine_config_model import EngineConfig
from app.models.tourism_catalog_model import TourismCatalog
from app.services.destination_metric_sync_service import recalculate_status

SEED_DIR = Path(__file__).resolve().parent.parent / "seed_data"

# La tesis (Fase 3, NB02/NB03) usa score_normalizado_0_1 de TODAS las filas de la matriz,
# sin filtrar por evidence_status. Se replica igual para reproducir sus rankings.



# Nivel de costo ESTIMADO de la visita típica por persona (entradas + la actividad principal;
# no incluye alojamiento ni el viaje hasta la ciudad). Criterio: bajo < S/ 30, medio S/ 30-100,
# alto > S/ 100. Son estimaciones del equipo basadas en tarifas habituales: verifícalas contra las
# tarifas oficiales y corrígelas desde el dashboard (Destinos > Editar > Nivel de costo estimado).
# Solo se cargan si el destino aún no tiene nivel, para no pisar lo que edites en el dashboard.
_COST_LEVELS = {
    "machu_picchu": "alto",          # entrada ~S/ 150+
    "lineas_nazca": "alto",          # la experiencia típica es el sobrevuelo (> S/ 300)
    "ollantaytambo": "medio",        # boleto turístico del Valle Sagrado
    "valle_colca": "medio",          # boleto turístico ~S/ 70
    "reserva_paracas": "medio",      # entrada + paseo a las Islas Ballestas
    "parque_huascaran": "medio",     # entrada + transporte/guía a las lagunas
    "ciudadela_kuelap": "medio",     # entrada + teleférico
    "chan_chan": "bajo",
    "huaca_luna": "bajo",
    "huaca_pucllana": "bajo",
    "museo_sipan": "bajo",
    "catarata_ahuashiyacu": "bajo",
    "parque_aguas": "bajo",
    "ventanillas_otuzco": "bajo",
}


def _load_content() -> dict:
    path = SEED_DIR / "destination_content.json"
    if not path.exists():
        return {}
    import json
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


CONTENT = _load_content()


def read(name: str) -> list[dict]:
    with open(SEED_DIR / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fnum(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main(dry_run: bool) -> None:
    registro = read("registro_maestro_centros_turisticos.csv")
    matriz = read("matriz_destino_aspecto_sentimiento.csv")
    clima = read("clima_scores.csv")
    aforo = read("aforo_scores.csv")

    ids = {r["destination_id"] for r in registro}
    for label, rows in (("matriz", matriz), ("clima", clima), ("aforo", aforo)):
        extra = {r["destination_id"] for r in rows} - ids
        if extra:
            raise SystemExit(f"{label} tiene destinos fuera del registro: {sorted(extra)}")

    # --- factores de tolerancia (sensibilidad por nivel) desde aforo_scores ---
    ftol = {}
    for r in aforo:
        ftol.setdefault(r["tolerancia_multitudes"], fnum(r["sensibilidad"]))

    db = SessionLocal()
    try:
        # 1) destinos + catálogo + tags
        for r in registro:
            did = r["destination_id"]
            dest = db.query(Destination).filter_by(destination_id=did).first()
            if not dest:
                dest = Destination(destination_id=did, destination=r["destination"], is_active=True)
                db.add(dest)
                db.flush()
            else:
                dest.destination = r["destination"]
            # Los 14 destinos de la tesis fueron entrenados/validados con el motor.
            dest.in_engine = True

            cat = db.query(TourismCatalog).filter_by(destination_id=did).first()
            if not cat:
                cat = TourismCatalog(destination_id=did)
                db.add(cat)
            cat.region = r["region"]
            if cat.cost_level is None and did in _COST_LEVELS:
                cat.cost_level = _COST_LEVELS[did]

            # Ficha comercial (borrador): solo llena campos vacíos, así no pisa lo editado en el dashboard.
            for field, value in CONTENT.get(did, {}).items():
                if value is not None and getattr(cat, field, None) is None:
                    setattr(cat, field, value)

            db.query(DestinationTag).filter_by(destination_id=did).delete()
            for tag in {t.strip().lower() for t in r["intereses"].split(",") if t.strip()}:
                db.add(DestinationTag(destination_id=did, tag=tag))

        # 2) ABSA
        db.flush()
        absa_cols = {c for c in DestinationAspectScore.__table__.columns.keys()}
        by_dest: dict[str, dict] = {}
        for m in matriz:
            if m["aspecto"] not in absa_cols:
                continue
            by_dest.setdefault(m["destination_id"], {})[m["aspecto"]] = fnum(m["score_normalizado_0_1"])
        for did in ids:
            row = db.query(DestinationAspectScore).filter_by(destination_id=did).first()
            if not row:
                row = DestinationAspectScore(destination_id=did)
                db.add(row)
            for aspecto, val in by_dest.get(did, {}).items():
                setattr(row, aspecto, val)

        # 3) contexto mensual: clima (preferencia 'indiferente', el motor personaliza) + aforo base
        aforo_base = {}
        for r in aforo:
            aforo_base.setdefault((r["destination_id"], int(r["mes_num"])), r)
        clima_pref: dict[tuple, dict] = {}
        for c in clima:
            clima_pref.setdefault((c["destination_id"], int(c["mes_num"])), {})[
                c["preferencia_climatica"]] = fnum(c["score_clima"])
        aforo_tol: dict[tuple, dict] = {}
        for r in aforo:
            aforo_tol.setdefault((r["destination_id"], int(r["mes_num"])), {})[
                r["tolerancia_multitudes"]] = fnum(r["score_aforo_personalizado"])

        n_ctx = 0
        for c in clima:
            if c["preferencia_climatica"] != "indiferente":
                continue
            did, mes = c["destination_id"], int(c["mes_num"])
            ctx = db.query(DestinationMonthContext).filter_by(destination_id=did, month=mes).first()
            if not ctx:
                ctx = DestinationMonthContext(destination_id=did, month=mes)
                db.add(ctx)
            tmax, tmin = fnum(c["tmax_c"]), fnum(c["tmin_c"])
            ctx.clima_score = fnum(c["score_clima"])
            ctx.clima_nivel = c["nivel_clima"]
            ctx.temp_prom = round((tmax + tmin) / 2, 1) if tmax is not None and tmin is not None else None
            ctx.pp = fnum(c["pp_mm"])
            ctx.clima_explicacion = (c.get("explicacion_clima") or "").strip() or None
            ctx.clima_riesgo = (c.get("riesgo_climatico") or "").strip() or None
            ctx.clima_por_preferencia = clima_pref[(did, mes)]
            ctx.aforo_por_tolerancia = aforo_tol[(did, mes)]
            a = aforo_base.get((did, mes))
            if a:
                ctx.aforo_score = fnum(a["score_aforo"])
                ctx.aforo_nivel = a["nivel_aforo"]
                ctx.aforo_fuente = "tesis_fase4"
                ctx.aforo_explicacion = (a.get("explicacion_aforo") or "").strip() or None
                ctx.visitantes_medios = fnum(a.get("visitantes_medios"))
            n_ctx += 1

        # 4) engine_config
        cfg = db.query(EngineConfig).first()
        if not cfg:
            cfg = EngineConfig()
            db.add(cfg)
        cfg.alpha_absa, cfg.beta_contexto = 0.25, 0.30   # tesis: Fase 3 alpha=0.25, Fase 4 w=0.30
        cfg.w_clima, cfg.w_aforo = 0.5, 0.5
        # Deprecados: la tolerancia ya viene aplicada en aforo_por_tolerancia.
        cfg.factor_tolerancia_baja = ftol.get("baja", 1.0)
        cfg.factor_tolerancia_media = ftol.get("media", 0.65)
        cfg.factor_tolerancia_alta = ftol.get("alta", 0.35)

        # 5) data_status
        db.flush()
        statuses = {did: recalculate_status(db, did) for did in sorted(ids)}

        print(f"Destinos: {len(ids)}")
        print(f"ABSA: {sum(len(v) for v in by_dest.values())} puntajes (aspectos con evidencia)")
        print(f"Contexto mensual: {n_ctx} filas")
        print(f"Factores de tolerancia: {ftol}")
        print(f"Estados: { {s: list(statuses.values()).count(s) for s in set(statuses.values())} }")

        if dry_run:
            db.rollback()
            print("DRY-RUN: sin cambios en BD.")
        else:
            db.commit()
            print("Seed aplicado.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    main(ap.parse_args().dry_run)
