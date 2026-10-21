"""
PROXVEL Backend - Destination Merge Service.
Fusiona dos destinos: migra todos los datos del origen al destino canónico
y elimina el origen.

Uso típico:
  - source: el duplicado a eliminar
  - target: el destino canónico a conservar

Estrategia de merge:
  - TourismCatalog: se conserva la del target; los campos NULL del target
    se rellenan con los del source si están disponibles.
  - ABSA: se conservan los del target si ya tienen valores reales;
    si no, se migran los del source.
  - Tags: unión (sin duplicados).
  - DestinationMonthContext: target gana en meses con conflicto;
    meses faltantes se migran del source.
  - Media, Reviews, Visits, Favorites: se reasignan al target.
  - ClimateScore, CrowdScore, ContextualRanking del source: se eliminan.
  - El Destination del source se elimina.
"""

import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.aspect_score_model import DestinationAspectScore
from app.models.destination_tag_model import DestinationTag
from app.models.destination_month_context_model import DestinationMonthContext
from app.models.climate_score_model import ClimateScore
from app.models.crowd_score_model import CrowdScore
from app.models.contextual_ranking_model import ContextualRanking
from app.models.destination_media_model import DestinationMedia
from app.models.favorite_model import Favorite
from app.models.review_model import Review
from app.models.visit_model import Visit
from app.services.destination_metric_sync_service import recalculate_status

logger = logging.getLogger(__name__)

_ABSA_FIELDS = [
    "accesibilidad", "aforo_multitudes", "alojamiento", "atencion_servicio",
    "atractivos", "clima", "costos", "gastronomia", "limpieza", "seguridad",
]
_EDITORIAL_FIELDS = [
    "region", "city", "category", "altitude_m", "description",
    "activities_summary", "visitor_info_summary", "accessibility_summary",
    "recommended_duration", "how_to_get", "difficulty", "official_website",
    "cost_level", "latitude", "longitude",
]


def merge_destinations(db: Session, source_id: str, target_id: str) -> dict[str, Any]:
    """
    Fusiona source → target. Elimina source al finalizar.
    Devuelve un resumen de lo que se migró.
    """
    if source_id == target_id:
        raise HTTPException(status_code=400, detail="El origen y el destino no pueden ser el mismo.")

    source = db.query(Destination).filter_by(destination_id=source_id).first()
    target = db.query(Destination).filter_by(destination_id=target_id).first()

    if not source:
        raise HTTPException(status_code=404, detail=f"Origen no encontrado: {source_id}")
    if not target:
        raise HTTPException(status_code=404, detail=f"Destino no encontrado: {target_id}")

    summary: dict[str, int] = {}

    try:
        # 1. Catálogo turístico — rellena campos vacíos del target con los del source
        src_cat = db.query(TourismCatalog).filter_by(destination_id=source_id).first()
        tgt_cat = db.query(TourismCatalog).filter_by(destination_id=target_id).first()
        if not tgt_cat:
            tgt_cat = TourismCatalog(destination_id=target_id)
            db.add(tgt_cat)
            db.flush()
        if src_cat:
            fields_filled = 0
            for field in _EDITORIAL_FIELDS:
                if not getattr(tgt_cat, field, None) and getattr(src_cat, field, None):
                    setattr(tgt_cat, field, getattr(src_cat, field))
                    fields_filled += 1
            summary["catalog_fields_filled"] = fields_filled

        # 2. ABSA — conserva target si tiene valores reales; si no, toma del source
        src_absa = db.query(DestinationAspectScore).filter_by(destination_id=source_id).first()
        tgt_absa = db.query(DestinationAspectScore).filter_by(destination_id=target_id).first()
        absa_migrated = False
        if src_absa:
            tgt_has_real = tgt_absa and any(getattr(tgt_absa, f) is not None for f in _ABSA_FIELDS)
            if not tgt_has_real:
                if tgt_absa:
                    for f in _ABSA_FIELDS:
                        setattr(tgt_absa, f, getattr(src_absa, f))
                else:
                    new_absa = DestinationAspectScore(
                        destination_id=target_id,
                        **{f: getattr(src_absa, f) for f in _ABSA_FIELDS},
                    )
                    db.add(new_absa)
                absa_migrated = True
            summary["absa_migrated"] = int(absa_migrated)

        # 3. Tags — unión
        src_tags = {t.tag for t in db.query(DestinationTag).filter_by(destination_id=source_id).all()}
        tgt_tags = {t.tag for t in db.query(DestinationTag).filter_by(destination_id=target_id).all()}
        new_tags = src_tags - tgt_tags
        for tag in new_tags:
            db.add(DestinationTag(destination_id=target_id, tag=tag))
        summary["tags_added"] = len(new_tags)

        # 4. DestinationMonthContext — target gana en conflicto; migra meses faltantes
        src_months = {
            c.month: c for c in db.query(DestinationMonthContext).filter_by(destination_id=source_id).all()
        }
        tgt_months = {
            c.month for c in db.query(DestinationMonthContext).filter_by(destination_id=target_id).all()
        }
        months_added = 0
        for month, ctx in src_months.items():
            if month not in tgt_months:
                db.add(DestinationMonthContext(
                    destination_id=target_id,
                    month=ctx.month,
                    clima_score=ctx.clima_score,
                    clima_nivel=ctx.clima_nivel,
                    temp_prom=ctx.temp_prom,
                    pp=ctx.pp,
                    aforo_score=ctx.aforo_score,
                    aforo_nivel=ctx.aforo_nivel,
                    aforo_fuente=ctx.aforo_fuente,
                ))
                months_added += 1
        summary["months_added"] = months_added

        # 5. Media — reasignar al target
        media_count = db.query(DestinationMedia).filter_by(destination_id=source_id).count()
        db.query(DestinationMedia).filter_by(destination_id=source_id).update(
            {"destination_id": target_id}, synchronize_session=False
        )
        summary["media_reassigned"] = media_count

        # 6. Reseñas — reasignar
        reviews_count = db.query(Review).filter_by(destination_id=source_id).count()
        db.query(Review).filter_by(destination_id=source_id).update(
            {"destination_id": target_id}, synchronize_session=False
        )
        summary["reviews_reassigned"] = reviews_count

        # 7. Visitas — reasignar
        visits_count = db.query(Visit).filter_by(destination_id=source_id).count()
        db.query(Visit).filter_by(destination_id=source_id).update(
            {"destination_id": target_id}, synchronize_session=False
        )
        summary["visits_reassigned"] = visits_count

        # 8. Favoritos — reasignar; eliminar duplicados (UniqueConstraint user+dest)
        fav_reassigned = 0
        for fav in db.query(Favorite).filter_by(destination_id=source_id).all():
            already = db.query(Favorite).filter_by(
                user_id=fav.user_id, destination_id=target_id
            ).first()
            if already:
                db.delete(fav)
            else:
                fav.destination_id = target_id
                fav_reassigned += 1
        summary["favorites_reassigned"] = fav_reassigned

        # 9. Eliminar datos del source que no se migran
        db.query(ClimateScore).filter_by(destination_id=source_id).delete(synchronize_session=False)
        db.query(CrowdScore).filter_by(destination_id=source_id).delete(synchronize_session=False)
        db.query(ContextualRanking).filter_by(destination_id=source_id).delete(synchronize_session=False)
        db.query(DestinationAspectScore).filter_by(destination_id=source_id).delete(synchronize_session=False)
        db.query(DestinationTag).filter_by(destination_id=source_id).delete(synchronize_session=False)
        db.query(DestinationMonthContext).filter_by(destination_id=source_id).delete(synchronize_session=False)
        if src_cat:
            db.delete(src_cat)
        db.flush()

        # 10. Eliminar el Destination origen
        db.delete(source)
        db.flush()

        # 11. Recalcular status del target
        recalculate_status(db, target_id)

        db.commit()

        logger.info(
            "Merge completado: %s → %s | resumen=%s",
            source_id, target_id, summary
        )
        return {
            "source_deleted": source_id,
            "target_kept": target_id,
            "summary": summary,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Error en merge %s → %s: %s", source_id, target_id, e)
        raise HTTPException(status_code=500, detail=f"Error al fusionar: {e}")
