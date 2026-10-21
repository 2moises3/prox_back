"""
PROXVEL Backend - Motor de Recomendación (alineado con la tesis, Fases 3 y 4).
Lee 100% desde PostgreSQL. Sin pandas, sin JSON, sin CSV.

Modelo (réplica de los notebooks de la tesis):

  Fase 3 - afinidad (por viajero, normalizada min-max sobre los destinos del motor)
      S_int  = |intereses del viajero ∩ tags del destino| / |intereses del viajero|
      S_absa = Σ peso_a · ABSA_a      (a ∈ limpieza, atencion_servicio, atractivos)
      afinidad = (1 - alpha_absa) · norm(S_int) + alpha_absa · norm(S_absa)      alpha_absa = 0.25

  Fase 4 - re-ranking contextual (por mes)
      C = w_clima · clima[preferencia] + w_aforo · aforo[tolerancia]             0.5 / 0.5
      score = afinidad + beta_contexto · (C - 0.5)                               beta = 0.30

  Etiqueta (Fase 3, NB02): se decide con la cobertura de intereses y la calidad
  absolutas (no con el score mezclado, que se normaliza por perfil).

Universo: destinos con is_active = True Y in_engine = True Y los 3 puntajes de
calidad cargados. Un destino puede ser visible en la app sin entrar al motor.

Presupuesto y días de viaje NO intervienen (la tesis los descarta: no hay tarifas
ni duraciones oficiales por destino con que compararlos).

Fuentes (BD):
  engine_config, destinations, destination_aspect_scores, destination_tags,
  destination_month_context (clima_por_preferencia / aforo_por_tolerancia),
  tourism_catalog.
"""
import logging
import unicodedata
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

# Aspectos de calidad del modelo (los únicos con precisión de detección >= 0.70).
_QUALITY = ["limpieza", "atencion_servicio", "atractivos"]
_ASPECT_LABEL = {
    "limpieza": "la limpieza",
    "atencion_servicio": "la atención al visitante",
    "atractivos": "los atractivos",
}

# Vocabulario de intereses de la tesis (debe coincidir con los tags de los destinos).
INTEREST_VOCAB = {
    "academico", "aventura", "cultura", "familiar", "fotografia", "gastronomia",
    "historia", "montanismo", "naturaleza", "playa", "relax", "rural", "urbano",
}

# Pesos de calidad por tipo de viajero (tesis, distribuciones_referencia.json).
_PESOS_POR_PERFIL = {
    "cultural":            {"limpieza": 0.35, "atencion_servicio": 0.45, "atractivos": 0.20},
    "naturalista":         {"limpieza": 0.50, "atencion_servicio": 0.30, "atractivos": 0.20},
    "familiar":            {"limpieza": 0.45, "atencion_servicio": 0.40, "atractivos": 0.15},
    "economico_mochilero": {"limpieza": 0.40, "atencion_servicio": 0.35, "atractivos": 0.25},
    "gastronomico":        {"limpieza": 0.40, "atencion_servicio": 0.45, "atractivos": 0.15},
    "aventurero":          {"limpieza": 0.35, "atencion_servicio": 0.30, "atractivos": 0.35},
    "urbano_recreativo":   {"limpieza": 0.45, "atencion_servicio": 0.40, "atractivos": 0.15},
}
# La app no guarda "perfil_turistico": se infiere del interés dominante.
_INTEREST_TO_TYPE = {
    "cultura": "cultural", "historia": "cultural", "academico": "cultural", "fotografia": "cultural",
    "naturaleza": "naturalista", "rural": "naturalista", "montanismo": "naturalista", "playa": "naturalista",
    "familiar": "familiar", "gastronomia": "gastronomico", "aventura": "aventurero",
    "urbano": "urbano_recreativo", "relax": "urbano_recreativo",
}

_CLIMATE_PREFS = {"frio", "templado", "calido", "seco", "indiferente"}
_NEUTRAL = 0.5

# Defaults si engine_config aún no está sembrado (valores de la tesis).
_DEFAULTS = {"alpha_absa": 0.25, "beta_contexto": 0.30, "w_clima": 0.5, "w_aforo": 0.5}

# Umbrales de la etiqueta (tesis, Fase 3 NB02).
_COBERTURA_ALTA = 0.50
_COBERTURA_MINIMA = 0.01
_CALIDAD_ACEPTABLE = 0.60

MONTH_NAMES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _norm(t) -> str:
    t = unicodedata.normalize("NFKD", str(t).strip().lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return "_".join(t.split())


def _clip(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _load_config(db: Session) -> dict:
    cfg = db.query(EngineConfig).first()
    if not cfg:
        return dict(_DEFAULTS)
    return {
        "alpha_absa": float(cfg.alpha_absa),
        "beta_contexto": float(cfg.beta_contexto),
        "w_clima": float(cfg.w_clima),
        "w_aforo": float(cfg.w_aforo),
    }


# ── Normalización del perfil de la app al vocabulario de la tesis ────────────

def _perfil_intereses(profile: dict) -> set[str]:
    """Intereses declarados dentro del vocabulario de la tesis (Compras/Negocios se ignoran)."""
    return {n for n in (_norm(i) for i in (profile.get("intereses") or [])) if n in INTEREST_VOCAB}


def _perfil_clima(profile: dict) -> str:
    p = _norm(profile.get("clima_preferido") or "indiferente")
    return p if p in _CLIMATE_PREFS else "indiferente"


def _perfil_tolerancia(profile: dict) -> str:
    t = _norm(profile.get("tolerancia_multitudes") or "media")
    if t in ("baja", "bajo"):
        return "baja"
    if t in ("alta", "alto"):
        return "alta"
    return "media"  # media / moderado / moderada / desconocido


def _pesos_calidad(profile: dict, intereses: set[str]) -> dict:
    """
    Pesos de los 3 aspectos de calidad (suman 1).
    1) Si el viajero ajustó los sliders peso_* (no todos iguales) se normalizan.
    2) Si no, se infiere el tipo de viajero (presupuesto bajo -> económico/mochilero;
       si no, interés dominante) y se usan los pesos de la tesis.
    3) Sin información: uniformes.
    """
    sliders = [profile.get(f"peso_{a}") for a in _QUALITY]
    if all(s is not None for s in sliders) and len({round(float(s), 6) for s in sliders}) > 1:
        tot = sum(float(s) for s in sliders) or 1.0
        return {a: float(s) / tot for a, s in zip(_QUALITY, sliders)}

    tipo = None
    if _norm(profile.get("presupuesto") or "") == "bajo":
        tipo = "economico_mochilero"
    else:
        votos: dict[str, int] = {}
        for i in sorted(intereses):
            t = _INTEREST_TO_TYPE.get(i)
            if t:
                votos[t] = votos.get(t, 0) + 1
        if votos:
            tipo = max(votos, key=lambda k: (votos[k], -list(_PESOS_POR_PERFIL).index(k)))
    if tipo:
        return dict(_PESOS_POR_PERFIL[tipo])
    return {a: 1 / len(_QUALITY) for a in _QUALITY}


# ── Núcleo del modelo ────────────────────────────────────────────────────────

def _rownorm(values: dict[str, float]) -> dict[str, float]:
    """Min-max sobre los destinos del motor; 0.5 si no hay rango (tesis: normalizar_filas)."""
    lo, hi = min(values.values()), max(values.values())
    rango = hi - lo
    if rango <= 1e-12:
        return {k: 0.5 for k in values}
    return {k: (v - lo) / rango for k, v in values.items()}


def _contexto(ctx, pref: str, tol: str, w_clima: float, w_aforo: float) -> float:
    """C en [0,1]: clima según la preferencia + aforo ya personalizado por tolerancia."""
    clima = None
    aforo = None
    if ctx is not None:
        clima = (ctx.clima_por_preferencia or {}).get(pref)
        if clima is None:
            clima = ctx.clima_score
        aforo = (ctx.aforo_por_tolerancia or {}).get(tol)
        if aforo is None:
            aforo = ctx.aforo_score
    clima = _NEUTRAL if clima is None else float(clima)
    aforo = _NEUTRAL if aforo is None else float(aforo)
    return w_clima * clima + w_aforo * aforo


def _etiqueta(cobertura: float, calidad: float) -> str:
    tematico = cobertura >= _COBERTURA_ALTA
    algo = cobertura >= _COBERTURA_MINIMA
    buena = calidad >= _CALIDAD_ACEPTABLE
    if tematico and buena:
        return "Recomendado"
    if algo or buena:
        return "Parcialmente recomendado"
    return "No recomendado"


def _explicar(intereses: set[str], tags: set[str], absa_vals: dict, best_month_name: str) -> str:
    comunes = sorted(intereses & tags)
    if comunes:
        partes = ["coincide con tu interés en " + ", ".join(comunes)]
    elif intereses:
        partes = ["no coincide con ninguno de tus intereses declarados (" + ", ".join(sorted(intereses)) + ")"]
    else:
        partes = []
    buenos = [a for a in _QUALITY if absa_vals[a] >= 0.70]
    malos = [a for a in _QUALITY if absa_vals[a] < 0.50]
    if buenos:
        partes.append("buena valoración de " + ", ".join(_ASPECT_LABEL[a] for a in buenos))
    if malos:
        partes.append("valoración baja de " + ", ".join(_ASPECT_LABEL[a] for a in malos))
    if best_month_name:
        partes.append(f"mejor mes para ir: {best_month_name}")
    texto = "; ".join(partes)
    return (texto[:1].upper() + texto[1:] + ".") if texto else "Recomendación personalizada."


def generate_recommendations(
    user_profile: dict, limit: int = 10,
    month: int | None = None, region: str | None = None,
) -> list[dict]:
    db: Session = SessionLocal()
    try:
        cfg = _load_config(db)
        alpha = cfg["alpha_absa"]
        beta_cx = cfg["beta_contexto"]
        w_clima, w_aforo = cfg["w_clima"], cfg["w_aforo"]

        mes = int(month) if month and 1 <= int(month) <= 12 else datetime.now().month
        region_f = _norm(region) if region else None

        intereses = _perfil_intereses(user_profile)
        pref = _perfil_clima(user_profile)
        tol = _perfil_tolerancia(user_profile)
        w = _pesos_calidad(user_profile, intereses)

        # Universo del motor: activos + in_engine (un solo query con catálogo y ABSA).
        rows = db.execute(
            select(Destination, TourismCatalog, DestinationAspectScore)
            .outerjoin(TourismCatalog, Destination.destination_id == TourismCatalog.destination_id)
            .outerjoin(DestinationAspectScore, Destination.destination_id == DestinationAspectScore.destination_id)
            .where(Destination.is_active.is_(True), Destination.in_engine.is_(True))
        ).all()

        universe = []
        for dest, cat, absa in rows:
            if absa is None or any(getattr(absa, a) is None for a in _QUALITY):
                logger.warning("Motor: %s está in_engine pero sin los 3 puntajes de calidad; se omite",
                               dest.destination_id)
                continue
            universe.append((dest, cat, absa))
        if not universe:
            logger.warning("Motor: no hay destinos elegibles (activos + in_engine + ABSA)")
            return []

        dest_ids = [d.destination_id for d, _, _ in universe]

        tags_by_dest: dict[str, set[str]] = {did: set() for did in dest_ids}
        for t in db.execute(
            select(DestinationTag).where(DestinationTag.destination_id.in_(dest_ids))
        ).scalars():
            tags_by_dest.setdefault(t.destination_id, set()).add(_norm(t.tag))

        ctx_by: dict[tuple[str, int], DestinationMonthContext] = {}
        for c in db.execute(
            select(DestinationMonthContext).where(DestinationMonthContext.destination_id.in_(dest_ids))
        ).scalars():
            ctx_by[(c.destination_id, c.month)] = c

        from app.services import destination_media_service
        covers = destination_media_service.get_covers_batch(db)

        # --- Fase 3: afinidad (normalizada sobre TODO el universo del motor) ---
        s_int: dict[str, float] = {}
        s_abs: dict[str, float] = {}
        absa_of: dict[str, dict] = {}
        for dest, _, absa in universe:
            did = dest.destination_id
            vals = {a: float(getattr(absa, a)) for a in _QUALITY}
            absa_of[did] = vals
            s_int[did] = (len(intereses & tags_by_dest[did]) / len(intereses)) if intereses else 0.0
            s_abs[did] = sum(w[a] * vals[a] for a in _QUALITY)
        n_int, n_abs = _rownorm(s_int), _rownorm(s_abs)
        afinidad = {did: (1 - alpha) * n_int[did] + alpha * n_abs[did] for did in dest_ids}

        # --- Fase 4: score por mes ---
        raw = []
        for dest, cat, _ in universe:
            did = dest.destination_id
            if region_f and _norm(cat.region if cat and cat.region else "") != region_f:
                continue

            def score_mes(m: int) -> float:
                c = _contexto(ctx_by.get((did, m)), pref, tol, w_clima, w_aforo)
                return afinidad[did] + beta_cx * (c - 0.5)

            score = score_mes(mes)
            best_m = max(range(1, 13), key=score_mes)
            ctx = ctx_by.get((did, mes))
            raw.append({
                "dest": dest, "cat": cat, "did": did,
                "score": score, "best_m": best_m, "best_s": score_mes(best_m),
                "clima_nivel": ctx.clima_nivel if ctx else "Sin dato",
                "aforo_nivel": ctx.aforo_nivel if ctx else "Sin dato",
            })

        raw.sort(key=lambda r: r["score"], reverse=True)

        items = []
        for rank, r in enumerate(raw[:limit], 1):
            did, cat = r["did"], r["cat"]
            score = r["score"]
            compat_score = round(_clip(score), 4)
            compat_pct = round(compat_score * 100)
            label = _etiqueta(s_int[did], s_abs[did])
            best_m = r["best_m"]
            best_m_name = MONTH_NAMES.get(best_m, "")
            mes_name = MONTH_NAMES.get(mes, "")
            top_aspects = sorted(
                [{"aspect": a, "user_weight": round(w[a], 3),
                  "destination_score": round(absa_of[did][a], 4),
                  "contribution": round(w[a] * absa_of[did][a], 4)} for a in _QUALITY],
                key=lambda x: x["contribution"], reverse=True,
            )
            items.append({
                "destination_id": did,
                "name": r["dest"].destination,
                "city": cat.city if cat else None,
                "region": cat.region if cat else None,
                "category": cat.category if cat else None,
                "cover_image_url": covers.get(did),
                "rating": None,
                "compatibility_score": compat_score,
                "compatibility_percent": compat_pct,
                "label": label,
                "month": mes,
                "month_name": mes_name,
                "best_month": best_m,
                "best_month_name": best_m_name,
                "context_status": f"Clima {r['clima_nivel']} · Aforo {r['aforo_nivel']} · {mes_name.capitalize()}",
                "ranking_position": rank,
                "has_real_scores": True,
                "explanation": {
                    "summary": _explicar(intereses, tags_by_dest[did], absa_of[did], best_m_name),
                    "top_aspects": top_aspects,
                },
            })
        return items

    except Exception:
        logger.exception("Motor de recomendación falló")
        return []
    finally:
        db.close()
