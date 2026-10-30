"""
PROXVEL Backend - Admin Metrics Service.
Métricas REALES calculadas desde tablas existentes.
No genera datos simulados (usuarios activos, CPU, etc. no se inventan).
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func, distinct
from sqlalchemy.orm import Session

from app.models.destination_model import Destination
from app.models.destination_media_model import DestinationMedia
from app.models.review_model import Review
from app.models.user_model import User
from app.models.announcement_model import Announcement
from app.repositories import announcement_repository


def get_overview(db: Session) -> dict:
    """Construye el overview de métricas reales del dashboard."""

    total_destinations = db.scalar(select(func.count(Destination.id))) or 0

    # Destinos con portada activa (cover is_active=True)
    destinations_with_cover = (
        db.scalar(
            select(func.count(distinct(DestinationMedia.destination_id))).where(
                DestinationMedia.media_type == "cover",
                DestinationMedia.is_active.is_(True),
            )
        )
        or 0
    )
    destinations_without_cover = max(total_destinations - destinations_with_cover, 0)

    # Destinos con al menos una multimedia activa (cover o gallery)
    destinations_with_media = (
        db.scalar(
            select(func.count(distinct(DestinationMedia.destination_id))).where(
                DestinationMedia.is_active.is_(True)
            )
        )
        or 0
    )
    destinations_without_media = max(total_destinations - destinations_with_media, 0)

    total_reviews = db.scalar(select(func.count(Review.id))) or 0
    total_users = db.scalar(select(func.count(User.id))) or 0

    # Usuarios por rol
    role_rows = db.execute(
        select(User.role, func.count(User.id)).group_by(User.role)
    ).all()
    users_by_role = {role: count for role, count in role_rows}

    # Marcadores de mapa (coordenadas válidas)
    try:
        from app.services import tourism_service

        map_markers = len(tourism_service.get_map_markers() or [])
    except Exception:
        map_markers = 0

    active_announcements = announcement_repository.count_active(db)
    total_announcements = db.scalar(select(func.count(Announcement.id))) or 0

    return {
        "destinations": {
            "total": total_destinations,
            "with_cover": destinations_with_cover,
            "without_cover": destinations_without_cover,
            "with_media": destinations_with_media,
            "without_media": destinations_without_media,
        },
        "map_markers": map_markers,
        "reviews": {"total": total_reviews},
        "users": {
            "total": total_users,
            "travelers": users_by_role.get("traveler", 0),
            "admins": users_by_role.get("admin", 0),
            "super_admins": users_by_role.get("super_admin", 0),
        },
        "announcements": {
            "total": total_announcements,
            "active": active_announcements,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def get_charts_data(db: Session) -> dict:
    """Construye datos formateados para los gráficos de la interfaz con alta precisión."""
    from app.models.tourism_catalog_model import TourismCatalog

    is_sqlite = (getattr(getattr(db, "bind", None), "dialect", None) and db.bind.dialect.name == "sqlite")
    if is_sqlite:
        date_expr_month = func.strftime('%Y-%m', User.created_at)
        date_expr_day = func.strftime('%Y-%m-%d', User.created_at)
        rev_date_expr_month = func.strftime('%Y-%m', Review.created_at)
    else:
        date_expr_month = func.to_char(User.created_at, 'YYYY-MM')
        date_expr_day = func.to_char(User.created_at, 'YYYY-MM-DD')
        rev_date_expr_month = func.to_char(Review.created_at, 'YYYY-MM')

    # Crecimiento de usuarios por mes histórico con acumulado
    user_rows = db.execute(
        select(date_expr_month.label('month'), func.count(User.id))
        .where(User.created_at.isnot(None))
        .group_by('month')
        .order_by('month')
    ).all()
    running_total = 0
    user_growth = []
    for row in user_rows:
        if row[0]:
            count = int(row[1])
            running_total += count
            user_growth.append({
                "month": row[0],
                "users": count,
                "cumulative": running_total,
            })

    # Crecimiento de usuarios día a día (últimos 30 días continuos para precisión)
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    base_users_count = db.scalar(
        select(func.count(User.id)).where(User.created_at < thirty_days_ago)
    ) or 0

    daily_rows = db.execute(
        select(date_expr_day.label('day'), func.count(User.id))
        .where(User.created_at >= thirty_days_ago)
        .group_by('day')
        .order_by('day')
    ).all()

    daily_map = {row[0]: int(row[1]) for row in daily_rows if row[0]}
    user_growth_daily = []
    current_cumulative = base_users_count

    for i in range(30, -1, -1):
        day_dt = now - timedelta(days=i)
        day_str = day_dt.strftime('%Y-%m-%d')
        day_users = daily_map.get(day_str, 0)
        current_cumulative += day_users
        user_growth_daily.append({
            "date": day_str,
            "day": day_dt.strftime('%d/%m'),
            "users": day_users,
            "cumulative": current_cumulative,
        })

    # Resumen de KPIs de crecimiento para tarjetas del gráfico
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    new_today = db.scalar(select(func.count(User.id)).where(User.created_at >= today_start)) or 0
    new_this_week = db.scalar(select(func.count(User.id)).where(User.created_at >= seven_days_ago)) or 0
    new_this_month = db.scalar(select(func.count(User.id)).where(User.created_at >= month_start)) or 0
    total_users = db.scalar(select(func.count(User.id))) or 0

    user_metrics = {
        "total": total_users,
        "new_today": new_today,
        "new_this_week": new_this_week,
        "new_this_month": new_this_month,
    }

    # Reseñas por mes
    review_rows = db.execute(
        select(rev_date_expr_month.label('month'), func.count(Review.id))
        .group_by('month')
        .order_by('month')
    ).all()
    reviews_by_month = [{"month": row[0], "reviews": row[1]} for row in review_rows if row[0]]

    # Destinos por categoría
    cat_rows = db.execute(
        select(TourismCatalog.category, func.count(TourismCatalog.id))
        .where(TourismCatalog.category.isnot(None))
        .group_by(TourismCatalog.category)
        .order_by(func.count(TourismCatalog.id).desc())
    ).all()
    destinations_by_category = [{"name": row[0] or "Sin categoría", "value": row[1]} for row in cat_rows]

    # Destinos por región
    reg_rows = db.execute(
        select(TourismCatalog.region, func.count(TourismCatalog.id))
        .where(TourismCatalog.region.isnot(None))
        .group_by(TourismCatalog.region)
        .order_by(func.count(TourismCatalog.id).desc())
        .limit(10) # Top 10 regiones para no saturar el gráfico
    ).all()
    destinations_by_region = [{"name": row[0] or "Sin región", "value": row[1]} for row in reg_rows]

    return {
        "user_growth": user_growth,
        "user_growth_daily": user_growth_daily,
        "user_metrics": user_metrics,
        "reviews_by_month": reviews_by_month,
        "destinations_by_category": destinations_by_category,
        "destinations_by_region": destinations_by_region,
    }


# ── Actividad reciente y prioridades (inicio del dashboard) ──────────────────

def _iso(dt) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def get_activity(db: Session, limit: int = 8) -> list[dict]:
    """Últimos eventos reales: registros, reseñas, fotos subidas, anuncios y versiones."""
    from app.models.app_release_model import AppRelease

    nombres = dict(db.execute(select(Destination.destination_id, Destination.destination)).all())
    eventos: list[dict] = []

    for u in db.scalars(select(User).where(User.role == "traveler", User.account_status != "deleted")
                        .order_by(User.created_at.desc()).limit(limit)):
        eventos.append({"type": "user", "title": u.name or "Nuevo viajero",
                        "subtitle": "Se registró en la app", "at": u.created_at, "link": "/usuarios"})
    for r in db.scalars(select(Review).order_by(Review.created_at.desc()).limit(limit)):
        eventos.append({"type": "review", "title": nombres.get(r.destination_id, r.destination_id),
                        "subtitle": f"Nueva reseña ({r.rating_general:.0f}★)", "at": r.created_at,
                        "link": f"/destinos/{r.destination_id}?tab=comments", "destination_id": r.destination_id})
    for m in db.scalars(select(DestinationMedia).order_by(DestinationMedia.created_at.desc()).limit(limit)):
        eventos.append({"type": "media", "title": nombres.get(m.destination_id, m.destination_id),
                        "subtitle": "Portada actualizada" if m.media_type == "cover" else "Foto agregada a la galería",
                        "at": m.created_at, "link": f"/destinos/{m.destination_id}?tab=multimedia",
                        "destination_id": m.destination_id})
    for a in db.scalars(select(Announcement).order_by(Announcement.updated_at.desc()).limit(limit)):
        nuevo = a.created_at and a.updated_at and abs((a.updated_at - a.created_at).total_seconds()) < 2
        eventos.append({"type": "announcement", "title": a.title,
                        "subtitle": "Anuncio creado" if nuevo else "Anuncio editado",
                        "at": a.updated_at, "link": f"/anuncios/{a.id}"})
    for rel in db.scalars(select(AppRelease).order_by(AppRelease.created_at.desc()).limit(limit)):
        eventos.append({"type": "release", "title": f"Versión {rel.version_name}",
                        "subtitle": "Publicada" if rel.is_published else "Registrada", "at": rel.created_at,
                        "link": "/versiones"})

    eventos = [e for e in eventos if e["at"] is not None]
    eventos.sort(key=lambda e: e["at"], reverse=True)
    return [{**e, "at": _iso(e["at"])} for e in eventos[:limit]]


def get_priorities(db: Session) -> dict:
    """Pendientes reales que el equipo puede resolver desde el dashboard."""
    reviews_pending = db.scalar(select(func.count(Review.id)).where(Review.status == "pending_processing")) or 0
    out_of_engine = db.scalar(select(func.count(Destination.id)).where(
        Destination.is_active.is_(True), Destination.in_engine.is_(False))) or 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    soon = now + timedelta(days=7)
    expiring = db.scalar(select(func.count(Announcement.id)).where(
        Announcement.is_active.is_(True), Announcement.ends_at.is_not(None),
        Announcement.ends_at >= now, Announcement.ends_at <= soon)) or 0
    return {
        "reviews_pending": reviews_pending,
        "destinations_out_of_engine": out_of_engine,
        "announcements_expiring_7d": expiring,
    }
