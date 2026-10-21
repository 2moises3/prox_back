"""
PROXVEL Backend - Contexto mensual de destinos (clima y afluencia de la tesis, Fase 4).

Alimenta en la app: los filtros de clima/afluencia del buscador, la explicación del mes en el
detalle y el calendario de 12 meses. Es solo lectura: no modifica el motor de recomendación.
"""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.destination_model import Destination
from app.models.destination_month_context_model import DestinationMonthContext
from app.services.recommendation_engine_v1 import (
    _load_config,
    _perfil_clima,
    _perfil_tolerancia,
)

logger = logging.getLogger(__name__)

MONTH_NAMES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}

# Umbrales de la tesis (Fase 4, NB01): favorable >= 0.70, moderado >= 0.50.
FAVORABLE = 0.70
MODERADO = 0.50


def climate_level(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= FAVORABLE:
        return "Favorable"
    if score >= MODERADO:
        return "Moderado"
    return "Desfavorable"


def month_context(db: Session, month: int) -> list[dict]:
    """Clima (por preferencia) y afluencia de todos los destinos activos en un mes."""
    rows = db.execute(
        select(DestinationMonthContext)
        .join(Destination, Destination.destination_id == DestinationMonthContext.destination_id)
        .where(Destination.is_active.is_(True), DestinationMonthContext.month == month)
        .order_by(DestinationMonthContext.destination_id)
    ).scalars().all()
    return [
        {
            "destination_id": c.destination_id,
            "month": c.month,
            "month_name": MONTH_NAMES.get(c.month),
            "clima_por_preferencia": c.clima_por_preferencia or {},
            "clima_score": c.clima_score,
            "clima_nivel": c.clima_nivel or climate_level(c.clima_score),
            "clima_riesgo": c.clima_riesgo,
            "aforo_nivel": c.aforo_nivel,       # Bajo | Medio | Alto (visitantes del mes)
            "aforo_score": c.aforo_score,
            "visitantes_medios": c.visitantes_medios,
        }
        for c in rows
    ]


def calendar(db: Session, destination_id: str, clima: str | None, tolerancia: str | None) -> dict | None:
    """
    Los 12 meses de un destino con el clima según la preferencia y el aforo según la tolerancia.
    El «mejor» y «peor» mes usan el mismo contexto C del motor, así que coinciden con el
    `best_month` que ve el usuario en sus recomendaciones.
    """
    dest = db.scalar(select(Destination).where(Destination.destination_id == destination_id))
    if dest is None:
        return None

    pref = _perfil_clima({"clima_preferido": clima})
    tol = _perfil_tolerancia({"tolerancia_multitudes": tolerancia})
    cfg = _load_config(db)
    w_clima, w_aforo = cfg["w_clima"], cfg["w_aforo"]

    ctxs = {
        c.month: c
        for c in db.scalars(
            select(DestinationMonthContext).where(DestinationMonthContext.destination_id == destination_id)
        ).all()
    }
    months = []
    for m in range(1, 13):
        c = ctxs.get(m)
        if c is None:
            months.append({"month": m, "month_name": MONTH_NAMES[m], "has_data": False})
            continue
        clima_score = (c.clima_por_preferencia or {}).get(pref, c.clima_score)
        aforo_score = (c.aforo_por_tolerancia or {}).get(tol, c.aforo_score)
        combined = None
        if clima_score is not None and aforo_score is not None:
            combined = round(w_clima * clima_score + w_aforo * aforo_score, 4)
        months.append({
            "month": m,
            "month_name": MONTH_NAMES[m],
            "has_data": True,
            "clima_score": clima_score,
            "clima_nivel": climate_level(clima_score),
            "clima_riesgo": c.clima_riesgo,
            "clima_explicacion": c.clima_explicacion,
            "temp_prom": c.temp_prom,
            "lluvia_mm": c.pp,
            "aforo_score": aforo_score,
            "aforo_nivel": c.aforo_nivel,
            "aforo_explicacion": c.aforo_explicacion,
            "visitantes_medios": c.visitantes_medios,
            "combined": combined,
        })

    scored = [m for m in months if m.get("combined") is not None]
    best = max(scored, key=lambda m: m["combined"])["month"] if scored else None
    worst = min(scored, key=lambda m: m["combined"])["month"] if scored else None
    return {
        "destination_id": destination_id,
        "destination": dest.destination,
        "preference": pref,
        "tolerance": tol,
        "best_month": best,
        "worst_month": worst,
        "months": months,
    }
