"""
PROXVEL Backend - Engine Admin Service.
Gestión desde el dashboard de los parámetros del motor y de qué destinos
participan en las recomendaciones (in_engine).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.services.thesis_engine import get_engine

_DEFAULTS = {"alpha_absa": .25, "beta_contexto": .30, "w_clima": .5, "w_aforo": .5}

_CONFIG_FIELDS = ("alpha_absa", "beta_contexto", "w_clima", "w_aforo")


def get_defaults() -> dict:
    return {k: _DEFAULTS[k] for k in _CONFIG_FIELDS}


def get_config(db: Session) -> dict:
    return get_defaults()


def update_config(db: Session, values: dict) -> dict:
    raise HTTPException(status_code=409, detail="Los parámetros pertenecen a la versión científica V3 y son de solo lectura.")


def eligibility(db: Session, destination_ids: list[str] | None = None) -> dict[str, list[str]]:
    if destination_ids is None:
        destination_ids = list(db.scalars(select(Destination.destination_id)).all())
    ids = set(get_engine().ids)
    return {did: [] if did in ids else ["No pertenece al snapshot científico V3"] for did in destination_ids}


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
