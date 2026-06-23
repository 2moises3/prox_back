"""
PROXVEL Backend - Destination Metric Sync Service.
Recalcula data_status para todos los destinos leyendo 100% de PostgreSQL.
Sin dependencia de archivos CSV ni pandas.

Reglas de data_status:
  out_of_engine : sin DestinationAspectScore real → motor no puede puntuar
  pending_info  : tiene ABSA, falta info editorial (city/region/category/description)
  ready         : tiene ABSA + info editorial completa
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.aspect_score_model import DestinationAspectScore

logger = logging.getLogger(__name__)

# Campos ABSA que deben tener al menos uno con valor real para estar en el motor.
_ABSA_CHECK = ["atractivos", "costos", "seguridad", "accesibilidad", "limpieza",
               "atencion_servicio", "gastronomia", "alojamiento"]

# Campos editoriales requeridos para estado "ready".
_EDITORIAL = ["city", "region", "category", "description"]


def compute_destination_status(
    catalog: TourismCatalog | None,
    absa: DestinationAspectScore | None,
) -> str:
    """
    Calcula el data_status correcto dado el estado actual del destino en BD.
    No hace queries — recibe los objetos ya cargados.
    """
    has_absa = absa is not None and any(
        getattr(absa, f, None) is not None for f in _ABSA_CHECK
    )
    if not has_absa:
        return "out_of_engine"

    has_editorial = catalog is not None and all(
        bool(getattr(catalog, f, None)) for f in _EDITORIAL
    )
    return "ready" if has_editorial else "pending_info"


def recalculate_status(db: Session, destination_id: str) -> str:
    """
    Recalcula y persiste el data_status de un único destino.
    Útil tras import de ABSA o edición editorial.
    Devuelve el nuevo status.
    """
    catalog = db.query(TourismCatalog).filter_by(destination_id=destination_id).first()
    if not catalog:
        catalog = TourismCatalog(destination_id=destination_id)
        db.add(catalog)
        db.flush()

    absa = db.query(DestinationAspectScore).filter_by(destination_id=destination_id).first()
    new_status = compute_destination_status(catalog, absa)

    if catalog.data_status != new_status:
        catalog.data_status = new_status
        logger.info("data_status recalculado: %s → %s", destination_id, new_status)

    return new_status


def sync_destinations_from_metrics(db: Session) -> dict[str, Any]:
    """
    Recalcula data_status para TODOS los destinos desde la BD.
    Reemplaza la versión anterior que leía archivos CSV.
    """
    destinations = db.query(Destination).all()
    dest_ids = [d.destination_id for d in destinations]

    # Carga en batch para no hacer N+1 queries.
    catalogs = {
        c.destination_id: c
        for c in db.query(TourismCatalog).filter(
            TourismCatalog.destination_id.in_(dest_ids)
        ).all()
    }
    absa_map = {
        a.destination_id: a
        for a in db.query(DestinationAspectScore).filter(
            DestinationAspectScore.destination_id.in_(dest_ids)
        ).all()
    }

    updated: list[str] = []
    counts: dict[str, int] = {"out_of_engine": 0, "pending_info": 0, "ready": 0}

    for dest in destinations:
        did = dest.destination_id
        catalog = catalogs.get(did)

        if not catalog:
            catalog = TourismCatalog(destination_id=did)
            db.add(catalog)
            db.flush()
            catalogs[did] = catalog

        absa = absa_map.get(did)
        new_status = compute_destination_status(catalog, absa)
        counts[new_status] = counts.get(new_status, 0) + 1

        if catalog.data_status != new_status:
            catalog.data_status = new_status
            updated.append(did)
            logger.info("Sync: %s → %s", did, new_status)

    db.commit()

    total = len(destinations)
    logger.info(
        "Sync completado: %d/%d actualizados | ready=%d pending=%d out=%d",
        len(updated), total,
        counts["ready"], counts["pending_info"], counts["out_of_engine"],
    )

    return {
        "updated": updated,
        "summary": {
            "total": total,
            "updated_count": len(updated),
            "ready": counts["ready"],
            "pending_info": counts["pending_info"],
            "out_of_engine": counts["out_of_engine"],
        },
    }
