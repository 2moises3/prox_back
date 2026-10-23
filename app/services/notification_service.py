"""
PROXVEL Backend - Notification Service.

Una sola lista por usuario, ordenada por llegada (como el centro de notificaciones de
cualquier red social), que mezcla:
  * anuncios publicados desde el dashboard, y
  * avisos personales generados por el sistema.

Los avisos personales se generan al consultar la lista (idempotente, sin tareas programadas):
  - perfil_listo     : el usuario ya tiene perfil viajero → lleva a sus recomendaciones.
  - mejor_mes        : el mes actual es el mejor mes (según su perfil) de uno de sus favoritos.
  - destino_nuevo    : se sumó al motor un destino posterior al registro del usuario.
  - seguridad        : cambio o restablecimiento de contraseña (lo crea el endpoint).
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.database import SessionLocal
from app.models.announcement_model import Announcement
from app.models.destination_model import Destination
from app.models.favorite_model import Favorite
from app.models.notification_model import AnnouncementRead, Notification, NotificationPreference
from app.models.traveler_profile_model import TravelerProfile
from app.models.user_model import User
from app.repositories import announcement_repository
from app.services import destination_context_service

logger = logging.getLogger(__name__)

MAX_AGE_DAYS = 60
MONTH_NAMES = destination_context_service.MONTH_NAMES


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso(dt: datetime | None) -> str | None:
    return dt.replace(tzinfo=timezone.utc).isoformat() if dt else None


# ── Creación ─────────────────────────────────────────────────────────────────

def _create(db: Session, user_id: str, kind: str, title: str, body: str,
            route: str | None = None, destination_id: str | None = None,
            dedupe_key: str | None = None) -> bool:
    """Crea un aviso. Devuelve False si ya existía (misma dedupe_key)."""
    try:
        with db.begin_nested():
            db.add(Notification(
                user_id=user_id, kind=kind, title=title, body=body, route=route,
                destination_id=destination_id, dedupe_key=dedupe_key,
            ))
        return True
    except IntegrityError:
        return False


def notify_user(user_id: str, kind: str, title: str, body: str,
                route: str | None = None, dedupe_key: str | None = None) -> None:
    """Crea un aviso desde cualquier parte del backend sin que un fallo afecte a quien lo llama."""
    db = SessionLocal()
    try:
        _create(db, user_id, kind, title, body, route=route, dedupe_key=dedupe_key)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("No se pudo crear el aviso '%s' para %s", kind, user_id)
    finally:
        db.close()


def _short(text: str | None, limit: int = 160) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def generate_personal(db: Session, user_id: str) -> None:
    """Crea los avisos personales que correspondan ahora (idempotente)."""
    user = db.scalar(select(User).where(User.user_id == user_id))
    if user is None:
        return
    now = _now()
    profile = db.scalar(select(TravelerProfile).where(TravelerProfile.user_id == user_id))

    from app.services.thesis_engine import get_engine
    ready = profile is not None and profile.perfil_turistico in get_engine().profile_weights and bool(profile.intereses)

    # 1) Perfil listo
    if ready:
        _create(db, user_id, "perfil_listo", "Tu perfil está listo",
                "Ya puedes ver recomendaciones hechas a tu medida en «Para ti».",
                route="/main", dedupe_key="perfil_listo")

    # 2) Mejor mes de los favoritos
    # A personalized season claim requires actual traveler preferences.
    favs = db.scalars(select(Favorite).where(Favorite.user_id == user_id)).all() if ready else []
    for fav in favs:
        dest = db.scalar(select(Destination).where(
            Destination.destination_id == fav.destination_id, Destination.is_active.is_(True)))
        if dest is None:
            continue
        cal = destination_context_service.calendar(
            db, dest.destination_id,
            profile.clima_preferido if profile else None,
            profile.tolerancia_multitudes if profile else None,
        )
        if not cal or cal["best_month"] != now.month:
            continue
        month = next((m for m in cal["months"] if m["month"] == now.month), {})
        detail = " ".join(filter(None, [month.get("clima_explicacion"), month.get("aforo_explicacion")]))
        _create(
            db, user_id, "mejor_mes", f"Es buen momento para ir a {dest.destination}",
            _short(f"{MONTH_NAMES[now.month].capitalize()} es el mejor mes para ti. {detail}"),
            route=f"/destination/{dest.destination_id}?source=notification&month={now.month}",
            destination_id=dest.destination_id,
            dedupe_key=f"mejor_mes:{dest.destination_id}:{now.year}-{now.month}",
        )

    # 3) Destinos nuevos en el motor, posteriores al registro del usuario
    if user.created_at is not None:
        newer = db.scalars(select(Destination).where(
            Destination.is_active.is_(True), Destination.in_engine.is_(True),
            Destination.created_at > user.created_at)).all()
        for dest in newer:
            _create(db, user_id, "destino_nuevo", f"Nuevo destino: {dest.destination}",
                    "Ya puedes descubrirlo y consultar información para tu visita.",
                    route=f"/destination/{dest.destination_id}?source=notification",
                    destination_id=dest.destination_id, dedupe_key=f"destino_nuevo:{dest.destination_id}")
    db.commit()


# ── Lista unificada ──────────────────────────────────────────────────────────

def _active_announcements(db: Session) -> list[Announcement]:
    return announcement_repository.list_public_active(db)


def _announcement_route(a: Announcement) -> str | None:
    """Ruta interna de la app o enlace https (la app lo abre en el navegador)."""
    url = (a.cta_url or "").strip()
    return url if url.startswith("/") or url.startswith("https://") else None


def preferences(db: Session, user_id: str) -> dict:
    row = db.get(NotificationPreference, user_id)
    return {key: getattr(row, key) if row else True
            for key in ("recommendations", "new_destinations", "announcements")}


def update_preferences(db: Session, user_id: str, updates: dict) -> dict:
    if updates:
        statement = insert(NotificationPreference).values(user_id=user_id, **updates)
        db.execute(statement.on_conflict_do_update(
            index_elements=["user_id"], set_=updates))
        db.commit()
        db.expire_all()
    return preferences(db, user_id)


def _feed_items(db: Session, user_id: str) -> list[dict]:
    generate_personal(db, user_id)
    prefs = preferences(db, user_id)

    cutoff = _now() - timedelta(days=MAX_AGE_DAYS)
    personal = db.scalars(
        select(Notification).where(Notification.user_id == user_id, Notification.created_at >= cutoff)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
    ).all()
    read_announcements = set(db.scalars(
        select(AnnouncementRead.announcement_id).where(AnnouncementRead.user_id == user_id)).all())

    items = []
    for n in personal:
        if n.kind in ("perfil_listo", "mejor_mes") and not prefs["recommendations"]:
            continue
        if n.kind == "destino_nuevo" and not prefs["new_destinations"]:
            continue
        items.append({
            "id": f"n-{n.id}", "type": "personal", "kind": n.kind, "title": n.title, "body": n.body,
            "image_url": None, "route": n.route, "cta_text": None,
            "created_at": _iso(n.created_at), "is_read": n.read_at is not None, "_ts": n.created_at,
        })
    for a in _active_announcements(db):
        if not prefs["announcements"]:
            continue
        ts = a.starts_at or a.created_at
        if ts < cutoff:
            continue
        items.append({
            "id": f"a-{a.id}", "type": "announcement", "kind": "anuncio", "title": a.title, "body": a.message,
            "image_url": a.background_image_url, "route": _announcement_route(a), "cta_text": a.cta_text,
            "created_at": _iso(ts), "is_read": a.id in read_announcements, "_ts": ts,
        })

    items.sort(key=lambda i: (i["_ts"], i["id"]), reverse=True)
    for i in items:
        i.pop("_ts")
    return items


def feed(db: Session, user_id: str, limit: int = 50, offset: int = 0) -> dict:
    items = _feed_items(db, user_id)
    unread = sum(1 for i in items if not i["is_read"])
    page = items[offset:offset + limit]
    next_offset = offset + len(page)
    return {"items": page, "unread_count": unread, "total_count": len(items),
            "has_more": next_offset < len(items),
            "next_offset": next_offset if next_offset < len(items) else None}


def get_item(db: Session, user_id: str, item_id: str) -> dict | None:
    return next((item for item in _feed_items(db, user_id) if item["id"] == item_id), None)


def unread_count(db: Session, user_id: str) -> int:
    return feed(db, user_id, limit=1)["unread_count"]


# ── Lectura ──────────────────────────────────────────────────────────────────

def mark_read(db: Session, user_id: str, item_id: str) -> bool:
    """Marca un ítem como leído. Devuelve False si no existe o no es del usuario."""
    kind, _, raw = item_id.partition("-")
    if not raw.isdigit():
        return False
    ident = int(raw)
    if kind == "n":
        n = db.scalar(select(Notification).where(Notification.id == ident, Notification.user_id == user_id))
        if n is None:
            return False
        if n.read_at is None:
            n.read_at = _now()
            db.commit()
        return True
    if kind == "a":
        if db.scalar(select(Announcement.id).where(Announcement.id == ident)) is None:
            return False
        exists = db.scalar(select(AnnouncementRead.id).where(
            AnnouncementRead.user_id == user_id, AnnouncementRead.announcement_id == ident))
        if exists is None:
            db.add(AnnouncementRead(user_id=user_id, announcement_id=ident, read_at=_now()))
            db.commit()
        return True
    return False


def mark_all_read(db: Session, user_id: str) -> int:
    now = _now()
    visible = {item["id"] for item in _feed_items(db, user_id) if not item["is_read"]}
    count = 0
    for n in db.scalars(select(Notification).where(
            Notification.user_id == user_id, Notification.read_at.is_(None))).all():
        if f"n-{n.id}" not in visible:
            continue
        n.read_at = now
        count += 1
    already = set(db.scalars(select(AnnouncementRead.announcement_id).where(
        AnnouncementRead.user_id == user_id)).all())
    for a in _active_announcements(db):
        if a.id not in already and f"a-{a.id}" in visible:
            db.add(AnnouncementRead(user_id=user_id, announcement_id=a.id, read_at=now))
            count += 1
    db.commit()
    return count
