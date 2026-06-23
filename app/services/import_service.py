"""
PROXVEL Backend - Import Service.
Parsea CSV subidos desde el dashboard → upsert en BD.
Soporta: absa, tags, clima, aforo.
Nuevos destinos detectados → is_active=False automáticamente.
"""
import csv
import io
import logging
from typing import Literal

from sqlalchemy.orm import Session

from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.aspect_score_model import DestinationAspectScore
from app.models.destination_tag_model import DestinationTag
from app.models.destination_month_context_model import DestinationMonthContext
from app.utils.normalizers import (
    generate_destination_id,
    destination_word_set,
    jaccard_similarity,
)
from app.services.destination_metric_sync_service import recalculate_status

logger = logging.getLogger(__name__)

ImportType = Literal["absa", "tags", "clima", "aforo"]

_ABSA_ASPECTS = [
    "accesibilidad", "aforo_multitudes", "alojamiento", "atencion_servicio",
    "atractivos", "clima", "costos", "gastronomia", "limpieza", "seguridad",
]

_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


_SIMILARITY_THRESHOLD = 0.5


def _find_similar(all_dests: list[Destination], name: str) -> Destination | None:
    """
    Busca un destino existente cuyo nombre sea suficientemente similar al dado.
    Usa Jaccard sobre palabras significativas (umbral 0.5).
    Evita crear duplicados con nombres como "Kuélap" vs "Ciudadela de Kuélap".
    """
    query_words = destination_word_set(name)
    if not query_words:
        return None
    best_score = 0.0
    best_dest = None
    for dest in all_dests:
        score = jaccard_similarity(query_words, destination_word_set(dest.destination))
        if score > best_score:
            best_score = score
            best_dest = dest
    return best_dest if best_score >= _SIMILARITY_THRESHOLD else None


def _get_or_create_destination(
    db: Session,
    name: str,
    all_dests: list[Destination] | None = None,
) -> tuple[Destination, bool, str | None]:
    """
    Devuelve (destination, created, similar_name_warning).
    1. Busca por slug exacto.
    2. Busca por nombre exacto.
    3. Busca por similitud Jaccard ≥ 0.5 (previene duplicados).
    4. Si nada coincide, crea destino nuevo.
    """
    dest_id = generate_destination_id(name)
    dest = db.query(Destination).filter_by(destination_id=dest_id).first()
    if not dest:
        dest = db.query(Destination).filter_by(destination=name).first()
    if dest:
        return dest, False, None

    # Similitud: usa la lista pre-cargada si está disponible (evita N+1)
    candidates = all_dests if all_dests is not None else db.query(Destination).all()
    similar = _find_similar(candidates, name)
    if similar:
        warning = (
            f"'{name}' parece duplicado de '{similar.destination}' "
            f"(ID: {similar.destination_id}). Se usó el existente."
        )
        logger.warning("Import dedup: %s", warning)
        return similar, False, warning

    dest = Destination(destination_id=dest_id, destination=name, is_active=False)
    db.add(dest)
    db.flush()
    db.add(TourismCatalog(destination_id=dest_id))
    candidates.append(dest)  # para que la misma fila no cree duplicado en el mismo CSV
    return dest, True, None


def _parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader]


def _to_float(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _parse_month(row: dict) -> int | None:
    raw = row.get("month")
    if raw not in (None, ""):
        try:
            return int(float(raw))
        except (ValueError, TypeError):
            pass
    name = (row.get("month_name") or "").strip().lower()
    return _MONTHS.get(name)


def _get_or_create_month_ctx(db: Session, dest_id: str, month: int) -> DestinationMonthContext:
    ctx = db.query(DestinationMonthContext).filter_by(
        destination_id=dest_id, month=month
    ).first()
    if not ctx:
        ctx = DestinationMonthContext(destination_id=dest_id, month=month)
        db.add(ctx)
    return ctx


def import_absa(db: Session, content: bytes) -> dict:
    rows = _parse_csv(content)
    all_dests = db.query(Destination).all()
    created = updated = errors = 0
    warnings: list[str] = []
    affected_ids: set[str] = set()

    for row in rows:
        name = (row.get("destination") or "").strip()
        if not name:
            errors += 1
            continue
        try:
            dest, is_new, warn = _get_or_create_destination(db, name, all_dests)
            if is_new:
                created += 1
            if warn:
                warnings.append(warn)
            scores = db.query(DestinationAspectScore).filter_by(
                destination_id=dest.destination_id
            ).first()
            if not scores:
                scores = DestinationAspectScore(destination_id=dest.destination_id)
                db.add(scores)
            for asp in _ABSA_ASPECTS:
                val = _to_float(row.get(asp))
                if val is not None:
                    setattr(scores, asp, val)
            affected_ids.add(dest.destination_id)
            updated += 1
        except Exception as e:
            logger.error("import_absa row error: %s — %s", name, e)
            errors += 1

    db.commit()
    for did in affected_ids:
        recalculate_status(db, did)
    if affected_ids:
        db.commit()

    return {
        "type": "absa",
        "rows_processed": len(rows),
        "destinations_created": created,
        "scores_updated": updated,
        "errors": errors,
        "warnings": warnings,
    }


def import_tags(db: Session, content: bytes) -> dict:
    """CSV: destination, tags_interes (string separado por comas). Reemplaza tags."""
    rows = _parse_csv(content)
    all_dests = db.query(Destination).all()
    created = updated = errors = 0
    warnings: list[str] = []

    for row in rows:
        name = (row.get("destination") or "").strip()
        tags_raw = (row.get("tags_interes") or "").strip()
        if not name:
            errors += 1
            continue
        try:
            dest, is_new, warn = _get_or_create_destination(db, name, all_dests)
            if is_new:
                created += 1
            if warn:
                warnings.append(warn)
            db.query(DestinationTag).filter_by(destination_id=dest.destination_id).delete()
            for tag in tags_raw.split(","):
                tag = tag.strip().lower()
                if tag:
                    db.add(DestinationTag(destination_id=dest.destination_id, tag=tag))
            updated += 1
        except Exception as e:
            logger.error("import_tags row error: %s — %s", name, e)
            errors += 1
    db.commit()
    return {
        "type": "tags",
        "rows_processed": len(rows),
        "destinations_created": created,
        "records_updated": updated,
        "errors": errors,
        "warnings": warnings,
    }


def import_clima(db: Session, content: bytes) -> dict:
    """CSV clima → destination_month_context (campos de clima)."""
    rows = _parse_csv(content)
    all_dests = db.query(Destination).all()
    created = updated = errors = 0
    warnings: list[str] = []

    for row in rows:
        name = (row.get("destination") or "").strip()
        month = _parse_month(row)
        if not name or not month:
            errors += 1
            continue
        try:
            dest, is_new, warn = _get_or_create_destination(db, name, all_dests)
            if is_new:
                created += 1
            if warn:
                warnings.append(warn)
            ctx = _get_or_create_month_ctx(db, dest.destination_id, month)
            ctx.clima_score = _to_float(row.get("score_clima_modelo")) \
                if row.get("score_clima_modelo") not in (None, "") \
                else _to_float(row.get("score_clima_base"))
            ctx.clima_nivel = (row.get("nivel_clima_modelo") or row.get("nivel_clima") or "").strip() or None
            ctx.temp_prom = _to_float(row.get("temp_prom"))
            ctx.pp = _to_float(row.get("pp"))
            updated += 1
        except Exception as e:
            logger.error("import_clima row error: %s — %s", name, e)
            errors += 1
    db.commit()
    return {
        "type": "clima",
        "rows_processed": len(rows),
        "destinations_created": created,
        "records_updated": updated,
        "errors": errors,
        "warnings": warnings,
    }


def import_aforo(db: Session, content: bytes) -> dict:
    """CSV aforo mensual → destination_month_context (campos de aforo)."""
    rows = _parse_csv(content)
    all_dests = db.query(Destination).all()
    created = updated = errors = 0
    warnings: list[str] = []

    for row in rows:
        name = (row.get("destination") or "").strip()
        month = _parse_month(row)
        if not name or not month:
            errors += 1
            continue
        try:
            dest, is_new, warn = _get_or_create_destination(db, name, all_dests)
            if is_new:
                created += 1
            if warn:
                warnings.append(warn)
            ctx = _get_or_create_month_ctx(db, dest.destination_id, month)
            ctx.aforo_score = _to_float(row.get("score_aforo_modelo")) \
                if row.get("score_aforo_modelo") not in (None, "") \
                else _to_float(row.get("score_aforo_base_promedio"))
            ctx.aforo_nivel = (row.get("nivel_aforo_modelo") or "").strip() or None
            ctx.aforo_fuente = "oficial_visitantes"
            updated += 1
        except Exception as e:
            logger.error("import_aforo row error: %s — %s", name, e)
            errors += 1
    db.commit()
    return {
        "type": "aforo",
        "rows_processed": len(rows),
        "destinations_created": created,
        "records_updated": updated,
        "errors": errors,
        "warnings": warnings,
    }


def import_csv(db: Session, import_type: ImportType, content: bytes) -> dict:
    if import_type == "absa":
        return import_absa(db, content)
    if import_type == "tags":
        return import_tags(db, content)
    if import_type == "clima":
        return import_clima(db, content)
    if import_type == "aforo":
        return import_aforo(db, content)
    return {"type": import_type, "status": "unknown", "message": "Tipo no soportado"}
