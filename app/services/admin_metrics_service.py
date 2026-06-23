"""
PROXVEL Backend - Admin Metrics Service.
Métricas REALES calculadas desde tablas existentes.
No genera datos simulados (usuarios activos, CPU, etc. no se inventan).
"""

from datetime import datetime, timezone

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
    """Construye datos formateados para los gráficos de la interfaz."""
    from app.models.tourism_catalog_model import TourismCatalog

    # Crecimiento de usuarios por mes
    # Usamos to_char que es nativo de PostgreSQL
    user_rows = db.execute(
        select(func.to_char(User.created_at, 'YYYY-MM').label('month'), func.count(User.id))
        .group_by('month')
        .order_by('month')
    ).all()
    user_growth = [{"month": row[0], "users": row[1]} for row in user_rows if row[0]]

    # Reseñas por mes
    review_rows = db.execute(
        select(func.to_char(Review.created_at, 'YYYY-MM').label('month'), func.count(Review.id))
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
        "reviews_by_month": reviews_by_month,
        "destinations_by_category": destinations_by_category,
        "destinations_by_region": destinations_by_region,
    }
