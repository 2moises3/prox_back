"""
PROXVEL Backend - Motor de Recomendación V1 (Fase 3+4).
Lee 100% desde PostgreSQL. Sin pandas, sin JSON, sin CSV.

Fuentes de datos (BD):
  - engine_config                  → parámetros del modelo
  - destinations (is_active=True)  → universo de recomendación
  - destination_aspect_scores      → ABSA por destino
  - destination_tags               → tags de interés
  - destination_month_context      → clima/aforo del mes actual
  - tourism_catalog                → metadatos (cover, city, region)
"""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.aspect_score_model import DestinationAspectScore
from app.models.destination_tag_model import DestinationTag
from app.models.destination_month_context_model import DestinationMonthContext
from app.models.engine_config_model import EngineConfig

logger = logging.getLogger(__name__)

# Aspectos "core" del WSM (los que el modelo pondera). Mismo set que destinos.json.
_CORE = [
    "atractivos", "costos", "seguridad", "accesibilidad", "limpieza",
    "atencion_servicio", "gastronomia", "alojamiento",
]
_NEUTRAL = 0.5

# Defaults si engine_config aún no está sembrado.
_DEFAULTS = {
    "alpha_afinidad": 0.85, "beta_intereses": 0.15, "beta_contexto": 0.30,
    "w_clima": 0.5, "w_aforo": 0.5,
    "factor_tolerancia": {"baja": 1.0, "media": 0.65, "alta": 0.35},
}


def _clip(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _norm(t: str) -> str:
    t = str(t).strip().lower()
    for a, b in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]:
        t = t.replace(a, b)
    return t


def _load_config(db: Session) -> dict:
    cfg = db.query(EngineConfig).first()
    if not cfg:
        return _DEFAULTS
    return {
        "alpha_afinidad": cfg.alpha_afinidad,
        "beta_intereses": cfg.beta_intereses,
        "beta_contexto": cfg.beta_contexto,
        "w_clima": cfg.w_clima,
        "w_aforo": cfg.w_aforo,
        "factor_tolerancia": {
            "baja": cfg.factor_tolerancia_baja,
            "media": cfg.factor_tolerancia_media,
            "alta": cfg.factor_tolerancia_alta,
        },
    }


def _pesos_desde_perfil(profile: dict) -> dict:
    intereses   = {_norm(i) for i in (profile.get("intereses") or [])}
    presupuesto = _norm(profile.get("presupuesto") or "medio")
    dias        = int(profile.get("dias_viaje") or 3)

    w = {
        "atractivos":      0.18 + 0.06 * ("cultura" in intereses) + 0.05 * ("naturaleza" in intereses)
                               + 0.03 * ("fotografia" in intereses) + 0.03 * ("aventura" in intereses),
        "costos":          {"bajo": 0.22, "medio": 0.12, "alto": 0.06}.get(presupuesto, 0.12),
        "seguridad":       0.12,
        "accesibilidad":   0.10 + 0.06 * (dias <= 2),
        "limpieza":        0.10,
        "atencion_servicio": 0.10,
        "gastronomia":     0.08 + 0.10 * ("gastronomia" in intereses),
        "alojamiento":     0.05 + 0.08 * (dias >= 3) + 0.04 * (dias >= 5),
    }
    s = sum(w.values()) or 1.0
    return {a: w[a] / s for a in _CORE}


def _afinidad_clima(pref: str, temp, pp) -> float:
    pref = _norm(pref or "indiferente")
    if "calido"   in pref: return 0.5 if temp is None else _clip((temp - 10) / (22 - 10))
    if "frio"     in pref: return 0.5 if temp is None else _clip((20 - temp) / (20 - 8))
    if "templado" in pref:
        if temp is None: return 0.5
        return _clip(1 - max(0.0, 12 - temp, temp - 24) / 8)
    if "seco"     in pref: return 0.5 if pp is None else _clip((180 - pp) / (180 - 30))
    return 0.5


def generate_recommendations(user_profile: dict, limit: int = 10) -> list[dict]:
    db: Session = SessionLocal()
    try:
        cfg = _load_config(db)
        alpha   = float(cfg["alpha_afinidad"])
        beta_in = float(cfg["beta_intereses"])
        beta_cx = float(cfg["beta_contexto"])
        w_clima = float(cfg["w_clima"])
        w_aforo = float(cfg["w_aforo"])
        ftol_map = cfg["factor_tolerancia"]

        mes = datetime.now().month
        w   = _pesos_desde_perfil(user_profile)

        intereses  = {_norm(i) for i in (user_profile.get("intereses") or [])}
        pref_clima = user_profile.get("clima_preferido") or "indiferente"
        tol        = _norm(user_profile.get("tolerancia_multitudes") or "media")
        ftol       = float(ftol_map.get(tol, ftol_map.get("media", 0.65)))

        # Universo: destinos activos + catálogo + ABSA (un solo query).
        rows = (
            db.execute(
                select(Destination, TourismCatalog, DestinationAspectScore)
                .outerjoin(TourismCatalog, Destination.destination_id == TourismCatalog.destination_id)
                .outerjoin(DestinationAspectScore, Destination.destination_id == DestinationAspectScore.destination_id)
                .where(Destination.is_active.is_(True))
            ).all()
        )
        if not rows:
            logger.warning("Motor V1: no hay destinos activos en BD")
            return []

        dest_ids = [d.destination_id for d, _, _ in rows]

        # Tags por destino (batch).
        tags_by_dest: dict[str, set[str]] = {did: set() for did in dest_ids}
        for t in db.execute(
            select(DestinationTag).where(DestinationTag.destination_id.in_(dest_ids))
        ).scalars():
            tags_by_dest.setdefault(t.destination_id, set()).add(_norm(t.tag))

        # Contexto del mes actual (batch).
        ctx_by_dest: dict[str, DestinationMonthContext] = {}
        for c in db.execute(
            select(DestinationMonthContext).where(
                DestinationMonthContext.destination_id.in_(dest_ids),
                DestinationMonthContext.month == mes,
            )
        ).scalars():
            ctx_by_dest[c.destination_id] = c

        raw = []
        for dest, cat, absa in rows:
            did = dest.destination_id
            absa_vals = {
                a: (getattr(absa, a) if absa and getattr(absa, a) is not None else _NEUTRAL)
                for a in _CORE
            }
            score_absa = sum(w.get(a, 0.0) * float(absa_vals[a]) for a in _CORE)

            tags      = tags_by_dest.get(did, set())
            match_int = (len(intereses & tags) / len(intereses)) if intereses else 0.0
            afinidad  = (1 - beta_in) * score_absa + beta_in * match_int

            ctx = ctx_by_dest.get(did)
            clima_score = ctx.clima_score if ctx and ctx.clima_score is not None else _NEUTRAL
            aforo_score = ctx.aforo_score if ctx and ctx.aforo_score is not None else _NEUTRAL
            temp_prom   = ctx.temp_prom if ctx else None
            pp          = ctx.pp if ctx else None
            clima_nivel = ctx.clima_nivel if ctx else "Sin dato"
            aforo_nivel = ctx.aforo_nivel if ctx else "Sin dato"

            afc        = _afinidad_clima(pref_clima, temp_prom, pp)
            clima_pers = _clip(clima_score * (0.7 + 0.6 * afc))
            aforo_pers = _clip(0.5 + (aforo_score - 0.5) * ftol)
            C          = w_clima * clima_pers + w_aforo * aforo_pers
            score      = _clip(alpha * afinidad + beta_cx * (C - 0.5))

            top_aspects = sorted(
                [{"aspect": a, "user_weight": round(w.get(a, 0.0), 3),
                  "destination_score": round(float(absa_vals[a]), 4),
                  "contribution": round(w.get(a, 0.0) * float(absa_vals[a]), 4)}
                 for a in _CORE],
                key=lambda x: x["contribution"], reverse=True,
            )[:3]

            raw.append({
                "destination_id":  did,
                "name":            dest.destination,
                "city":            cat.city if cat else None,
                "region":          cat.region if cat else None,
                "category":        cat.category if cat else None,
                "cover_image_url": cat.cover_image_url if cat else None,
                "score":           score,
                "clima_nivel":     clima_nivel,
                "aforo_nivel":     aforo_nivel,
                "has_real_scores": absa is not None,
                "top_aspects":     top_aspects,
            })

        raw.sort(key=lambda r: r["score"], reverse=True)
        top = raw[:limit]

        items = []
        for rank, r in enumerate(top, 1):
            compat_score = round(r["score"], 4)
            compat_pct   = round(compat_score * 100)
            items.append({
                "destination_id":        r["destination_id"],
                "name":                  r["name"],
                "city":                  r["city"],
                "region":                r["region"],
                "category":              r["category"],
                "cover_image_url":       r["cover_image_url"],
                "rating":                None,
                "compatibility_score":   compat_score,
                "compatibility_percent": compat_pct,
                "context_status":        f"Clima {r['clima_nivel']} · Aforo {r['aforo_nivel']}",
                "ranking_position":      rank,
                "has_real_scores":       r["has_real_scores"],
                "explanation": {
                    "summary":     f"{compat_pct}% de compatibilidad con tu perfil de viaje",
                    "top_aspects": r["top_aspects"],
                },
            })
        return items

    except Exception as e:
        logger.error("Motor V1 error: %s", e)
        return []
    finally:
        db.close()
