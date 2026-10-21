"""
PROXVEL Backend - Engine Admin Service.
Gestión desde el dashboard de los parámetros del motor y de qué destinos
participan en las recomendaciones (in_engine).
"""
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.aspect_score_model import DestinationAspectScore
from app.models.destination_model import Destination
from app.models.destination_month_context_model import DestinationMonthContext
from app.models.destination_tag_model import DestinationTag
from app.models.engine_config_model import EngineConfig
from app.models.tourism_catalog_model import TourismCatalog
from app.services.recommendation_engine_v1 import _DEFAULTS, _QUALITY

logger = logging.getLogger(__name__)

_CONFIG_FIELDS = ("alpha_absa", "beta_contexto", "w_clima", "w_aforo")


def get_defaults() -> dict:
    return {k: _DEFAULTS[k] for k in _CONFIG_FIELDS}


def get_config(db: Session) -> dict:
    cfg = db.query(EngineConfig).first()
    if not cfg:
        return get_defaults()
    return {k: float(getattr(cfg, k)) for k in _CONFIG_FIELDS}


def update_config(db: Session, values: dict) -> dict:
    cfg = db.query(EngineConfig).first()
    if not cfg:
        cfg = EngineConfig()
        db.add(cfg)
    for k in _CONFIG_FIELDS:
        setattr(cfg, k, float(values[k]))
    db.commit()
    logger.info("Parámetros del motor actualizados: %s", values)
    return get_config(db)


def eligibility(db: Session, destination_ids: list[str] | None = None) -> dict[str, list[str]]:
    """
    Qué le falta a cada destino para poder entrar al motor. Lista vacía = elegible.
    Requisitos: los 3 puntajes de calidad ABSA, 12 meses de contexto (clima y aforo)
    y al menos un tag de interés.
    """
    if destination_ids is None:
        destination_ids = list(db.scalars(select(Destination.destination_id)).all())

    absa = {
        a.destination_id: a
        for a in db.scalars(
            select(DestinationAspectScore).where(DestinationAspectScore.destination_id.in_(destination_ids))
        ).all()
    }
    months: dict[str, int] = {}
    for did, n in db.execute(
        select(DestinationMonthContext.destination_id, func.count())
        .where(
            DestinationMonthContext.destination_id.in_(destination_ids),
            DestinationMonthContext.clima_score.is_not(None),
            DestinationMonthContext.aforo_score.is_not(None),
        )
        .group_by(DestinationMonthContext.destination_id)
    ).all():
        months[did] = n
    tags: dict[str, int] = {}
    for did, n in db.execute(
        select(DestinationTag.destination_id, func.count())
        .where(DestinationTag.destination_id.in_(destination_ids))
        .group_by(DestinationTag.destination_id)
    ).all():
        tags[did] = n

    result: dict[str, list[str]] = {}
    for did in destination_ids:
        missing: list[str] = []
        row = absa.get(did)
        if row is None or any(getattr(row, a) is None for a in _QUALITY):
            missing.append("Puntajes ABSA de limpieza, atención y atractivos")
        if months.get(did, 0) < 12:
            missing.append(f"Clima y aforo de los 12 meses (tiene {months.get(did, 0)})")
        if tags.get(did, 0) == 0:
            missing.append("Tags de interés")
        result[did] = missing
    return result


def universe(db: Session) -> list[dict]:
    """Todos los destinos con su participación en el motor y lo que les falta."""
    dests = db.scalars(select(Destination).order_by(Destination.destination)).all()
    ids = [d.destination_id for d in dests]
    miss = eligibility(db, ids)
    catalogs = {
        c.destination_id: c
        for c in db.scalars(select(TourismCatalog).where(TourismCatalog.destination_id.in_(ids))).all()
    }
    out = []
    for d in dests:
        cat = catalogs.get(d.destination_id)
        out.append({
            "destination_id": d.destination_id,
            "destination": d.destination,
            "region": cat.region if cat else None,
            "is_active": d.is_active,
            "in_engine": d.in_engine,
            "eligible": not miss[d.destination_id],
            "missing": miss[d.destination_id],
            # Participa de verdad en las recomendaciones de hoy.
            "recommendable": bool(d.is_active and d.in_engine and not miss[d.destination_id]),
        })
    return out


def set_in_engine(db: Session, destination_id: str, in_engine: bool) -> tuple[dict | None, str | None]:
    """Devuelve (resultado, error). Para incluir exige que el destino sea elegible."""
    dest = db.scalar(select(Destination).where(Destination.destination_id == destination_id))
    if not dest:
        return None, "not_found"
    if in_engine:
        missing = eligibility(db, [destination_id])[destination_id]
        if missing:
            return None, "No se puede incluir en el motor. Falta: " + "; ".join(missing) + "."
    dest.in_engine = in_engine
    db.commit()
    return {"destination_id": destination_id, "in_engine": dest.in_engine}, None
