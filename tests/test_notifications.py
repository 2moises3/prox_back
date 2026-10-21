"""
Centro de notificaciones (campana): lista única de anuncios + avisos personales, lectura por
usuario, generación idempotente y seguridad.

Crea usuarios (prefijo ZNOT) y anuncios temporales y los elimina al terminar.
Necesita los datos de `python scripts/seed_from_thesis.py` para los avisos de «mejor mes».
"""
from datetime import datetime, timedelta, timezone
import os

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config.database import SessionLocal
from app.core.security import create_access_token
from app.models.announcement_model import Announcement
from app.models.destination_model import Destination
from app.models.destination_month_context_model import DestinationMonthContext
from app.models.favorite_model import Favorite
from app.models.notification_model import AnnouncementRead, Notification
from app.models.traveler_profile_model import TravelerProfile
from app.models.user_model import User
from app.services import destination_context_service, notification_service
from app.utils.hash_util import get_password_hash

API = "/api/v1"
A, B = "ZNOT_A", "ZNOT_B"
DEST = "machu_picchu"
TAG = "ZNOT-test"


def hdr(uid):
    return {"Authorization": f"Bearer {create_access_token({'sub': uid})}"}


def naive_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@pytest.fixture(scope="module", autouse=True)
def isolated_calendar():
    """Explicit synthetic calendar only in the disposable verification database."""
    if os.environ.get("PROXVEL_ISOLATED_NOTIFICATIONS_TEST") != "1":
        yield
        return
    from app.config.database import engine
    assert engine.url.database.startswith("proxvel_notif_test_")
    db = SessionLocal()
    assert db.query(Destination).filter_by(destination_id=DEST).first() is None
    db.add(Destination(destination_id=DEST, destination="Machu Picchu",
                       created_at=datetime(2020, 1, 1), in_engine=False))
    db.flush()
    best = naive_now().month
    for month in range(1, 13):
        score = 0.9 if month == best else 0.2 + month / 100
        db.add(DestinationMonthContext(destination_id=DEST, month=month,
                                       clima_score=score, aforo_score=score))
    db.commit()
    yield
    db.query(DestinationMonthContext).filter_by(destination_id=DEST).delete()
    db.query(Destination).filter_by(destination_id=DEST).delete()
    db.commit()
    db.close()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _purge(db):
    db.query(Announcement).filter(Announcement.title.like(f"{TAG}%")).delete(synchronize_session=False)
    for uid in (A, B):
        db.query(Notification).filter_by(user_id=uid).delete()
        db.query(AnnouncementRead).filter_by(user_id=uid).delete()
        db.query(Favorite).filter_by(user_id=uid).delete()
        db.query(TravelerProfile).filter_by(user_id=uid).delete()
    db.query(User).filter(User.user_id.in_([A, B])).delete(synchronize_session=False)
    db.commit()


@pytest.fixture(autouse=True)
def fresh():
    db = SessionLocal()
    _purge(db)
    for uid in (A, B):
        db.add(User(user_id=uid, name=uid, email=f"{uid.lower()}@mailinator.com",
                    password_hash=get_password_hash("ClaveSegura123"), role="traveler",
                    is_active=True, account_status="active"))
    db.commit()
    yield db
    _purge(db)
    db.close()


def add_profile(db, uid):
    db.add(TravelerProfile(user_id=uid, presupuesto="medio", dias_viaje=3, clima_preferido="calido",
                           tipo_interes="mixto", intereses=["cultura"], tolerancia_multitudes="media"))
    db.commit()


def add_announcement(db, title, **kw):
    a = Announcement(title=f"{TAG} {title}", message="Mensaje de prueba", placement="home_top",
                     is_active=True, **kw)
    db.add(a)
    db.commit()
    return a


def feed(client, uid):
    r = client.get(f"{API}/notifications", headers=hdr(uid))
    assert r.status_code == 200
    return r.json()["data"]


def test_requiere_sesion(client):
    assert client.get(f"{API}/notifications").status_code == 401
    assert client.get(f"{API}/notifications/unread-count").status_code == 401
    assert client.post(f"{API}/notifications/read-all").status_code == 401


def test_usuario_nuevo_sin_nada_ve_lista_vacia(client):
    data = feed(client, A)
    assert [i for i in data["items"] if i["type"] == "personal"] == []


def test_perfil_listo_se_crea_una_sola_vez(client, fresh):
    add_profile(fresh, A)
    first = [i for i in feed(client, A)["items"] if i["kind"] == "perfil_listo"]
    again = [i for i in feed(client, A)["items"] if i["kind"] == "perfil_listo"]
    assert len(first) == 1 and len(again) == 1
    assert first[0]["route"] == "/main" and first[0]["is_read"] is False


def test_anuncios_del_dashboard_aparecen_y_se_leen_por_usuario(client, fresh):
    ann = add_announcement(fresh, "Oferta", cta_text="Ver", cta_url="/search")
    item = next(i for i in feed(client, A)["items"] if i["id"] == f"a-{ann.id}")
    assert item["type"] == "announcement" and item["route"] == "/search" and item["is_read"] is False

    assert client.post(f"{API}/notifications/a-{ann.id}/read", headers=hdr(A)).status_code == 200
    assert next(i for i in feed(client, A)["items"] if i["id"] == f"a-{ann.id}")["is_read"] is True
    # B no la leyó
    assert next(i for i in feed(client, B)["items"] if i["id"] == f"a-{ann.id}")["is_read"] is False


def test_anuncios_inactivos_o_vencidos_no_salen(client, fresh):
    inactivo = add_announcement(fresh, "Inactivo")
    inactivo.is_active = False
    vencido = add_announcement(fresh, "Vencido", ends_at=naive_now() - timedelta(days=1))
    futuro = add_announcement(fresh, "Futuro", starts_at=naive_now() + timedelta(days=2))
    fresh.commit()
    ids = {i["id"] for i in feed(client, A)["items"]}
    assert not ids & {f"a-{inactivo.id}", f"a-{vencido.id}", f"a-{futuro.id}"}


def test_enlace_https_se_ofrece_y_otros_esquemas_no(client, fresh):
    # La app abre los enlaces https en el navegador; cualquier otro esquema se descarta.
    ok = add_announcement(fresh, "Externo", cta_url="https://ejemplo.com/promo")
    malo = add_announcement(fresh, "Inseguro", cta_url="http://ejemplo.com/promo")
    items = {i["id"]: i for i in feed(client, A)["items"]}
    assert items[f"a-{ok.id}"]["route"] == "https://ejemplo.com/promo"
    assert items[f"a-{malo.id}"]["route"] is None


def test_orden_por_llegada_mezclando_anuncios_y_avisos(client, fresh):
    add_profile(fresh, A)
    viejo = add_announcement(fresh, "Viejo", starts_at=naive_now() - timedelta(days=3))
    nuevo = add_announcement(fresh, "Nuevo", starts_at=naive_now() + timedelta(seconds=-1))
    items = feed(client, A)["items"]
    orden = [i["id"] for i in items]
    assert orden.index(f"a-{nuevo.id}") < orden.index(f"a-{viejo.id}")
    stamps = [i["created_at"] for i in items]
    assert stamps == sorted(stamps, reverse=True)


def test_marcar_leidos_baja_el_conteo(client, fresh):
    add_profile(fresh, A)
    add_announcement(fresh, "Uno")
    n0 = client.get(f"{API}/notifications/unread-count", headers=hdr(A)).json()["data"]["unread_count"]
    assert n0 >= 2
    personal = next(i for i in feed(client, A)["items"] if i["type"] == "personal")
    assert client.post(f"{API}/notifications/{personal['id']}/read", headers=hdr(A)).status_code == 200
    n1 = client.get(f"{API}/notifications/unread-count", headers=hdr(A)).json()["data"]["unread_count"]
    assert n1 == n0 - 1
    assert client.post(f"{API}/notifications/read-all", headers=hdr(A)).status_code == 200
    assert client.get(f"{API}/notifications/unread-count", headers=hdr(A)).json()["data"]["unread_count"] == 0
    assert all(i["is_read"] for i in feed(client, A)["items"])


def test_no_se_puede_leer_el_aviso_de_otro_usuario(client, fresh):
    add_profile(fresh, A)
    mine = next(i for i in feed(client, A)["items"] if i["type"] == "personal")
    assert client.post(f"{API}/notifications/{mine['id']}/read", headers=hdr(B)).status_code == 404
    assert client.post(f"{API}/notifications/n-999999/read", headers=hdr(A)).status_code == 404
    assert client.post(f"{API}/notifications/xyz/read", headers=hdr(A)).status_code == 404


def test_no_se_ve_el_aviso_personal_de_otro(client, fresh):
    add_profile(fresh, A)
    feed(client, A)
    assert [i for i in feed(client, B)["items"] if i["kind"] == "perfil_listo"] == []


def test_mejor_mes_de_un_favorito_genera_aviso_una_sola_vez(client, fresh, monkeypatch):
    if fresh.query(Destination).filter_by(destination_id=DEST).first() is None:
        pytest.skip("BD sin datos: ejecuta scripts/seed_from_thesis.py")
    add_profile(fresh, A)
    fresh.add(Favorite(user_id=A, destination_id=DEST))
    fresh.commit()

    cal = destination_context_service.calendar(fresh, DEST, "calido", "media")
    best = cal["best_month"]
    # El «ahora» del servicio cae en el mejor mes del favorito.
    monkeypatch.setattr(notification_service, "_now", lambda: datetime(2026, best, 15, 12, 0))

    items = [i for i in feed(client, A)["items"] if i["kind"] == "mejor_mes"]
    assert len(items) == 1
    assert f"/destination/{DEST}" in items[0]["route"] and f"month={best}" in items[0]["route"]
    assert "Machu Picchu" in items[0]["title"]
    # Consultar de nuevo no duplica.
    assert len([i for i in feed(client, A)["items"] if i["kind"] == "mejor_mes"]) == 1


def test_no_hay_aviso_si_el_mes_no_es_el_mejor(client, fresh, monkeypatch):
    if fresh.query(Destination).filter_by(destination_id=DEST).first() is None:
        pytest.skip("BD sin datos: ejecuta scripts/seed_from_thesis.py")
    add_profile(fresh, A)
    fresh.add(Favorite(user_id=A, destination_id=DEST))
    fresh.commit()
    worst = destination_context_service.calendar(fresh, DEST, "calido", "media")["worst_month"]
    monkeypatch.setattr(notification_service, "_now", lambda: datetime(2026, worst, 15, 12, 0))
    assert [i for i in feed(client, A)["items"] if i["kind"] == "mejor_mes"] == []


def test_cambiar_contrasena_deja_un_aviso_de_seguridad(client):
    r = client.post(f"{API}/auth/change-password", headers=hdr(A),
                    json={"current_password": "ClaveSegura123", "new_password": "OtraClaveSegura456"})
    assert r.status_code == 200
    nuevo = r.json()["data"]["access_token"]
    items = client.get(f"{API}/notifications", headers={"Authorization": f"Bearer {nuevo}"}).json()["data"]["items"]
    assert any(i["kind"] == "seguridad" and "contraseña" in i["title"].lower() for i in items)


def test_al_borrar_el_usuario_se_borran_sus_avisos(client, fresh):
    add_profile(fresh, B)
    feed(client, B)
    assert fresh.query(Notification).filter_by(user_id=B).count() >= 1
    fresh.query(TravelerProfile).filter_by(user_id=B).delete()
    fresh.query(User).filter_by(user_id=B).delete()
    fresh.commit()
    assert fresh.query(Notification).filter_by(user_id=B).count() == 0


def test_preferences_are_per_account_and_security_cannot_be_disabled(client, fresh):
    defaults = {"recommendations": True, "new_destinations": True, "announcements": True}
    assert client.get(f"{API}/notifications/preferences", headers=hdr(A)).json()["data"] == defaults
    add_profile(fresh, A)
    add_announcement(fresh, "Preferencias")
    notification_service.notify_user(A, "seguridad", "Seguridad", "Un aviso de seguridad.")
    before = feed(client, A)
    assert any(item["kind"] == "perfil_listo" for item in before["items"])
    response = client.patch(f"{API}/notifications/preferences", headers=hdr(A),
                            json={"recommendations": False, "announcements": False, "new_destinations": False})
    assert response.status_code == 200
    visible = feed(client, A)
    assert visible["items"] and all(item["kind"] == "seguridad" for item in visible["items"])
    assert visible["unread_count"] == 1
    assert client.get(f"{API}/notifications/preferences", headers=hdr(B)).json()["data"] == defaults
    assert client.patch(f"{API}/notifications/preferences", headers=hdr(A),
                        json={"security": False}).status_code == 422
    assert client.patch(f"{API}/notifications/preferences", headers=hdr(A),
                        json={"recommendations": "false"}).status_code == 422
    assert client.get(f"{API}/notifications/preferences").status_code == 401
    assert client.patch(f"{API}/notifications/preferences", json={"announcements": False}).status_code == 401


def test_read_all_respects_visible_preferences_and_reenable_retains_unread(client, fresh):
    add_profile(fresh, A)
    announcement = add_announcement(fresh, "Oculto")
    feed(client, A)
    client.patch(f"{API}/notifications/preferences", headers=hdr(A), json={"announcements": False})
    assert client.post(f"{API}/notifications/read-all", headers=hdr(A)).status_code == 200
    client.patch(f"{API}/notifications/preferences", headers=hdr(A), json={"announcements": True})
    item = next(item for item in feed(client, A)["items"] if item["id"] == f"a-{announcement.id}")
    assert item["is_read"] is False
    assert next(item for item in feed(client, A)["items"] if item["kind"] == "perfil_listo")["is_read"] is True


def test_pagination_and_direct_message_keep_account_scope(client, fresh):
    for index in range(65):
        fresh.add(Notification(user_id=A, kind="seguridad", title=f"Aviso {index}",
                               body="Prueba de paginación", dedupe_key=f"page:{index}"))
    fresh.commit()
    pages = [client.get(f"{API}/notifications?limit=30&offset={offset}", headers=hdr(A)).json()["data"]
             for offset in (0, 30, 60)]
    personal = [item["id"] for page in pages for item in page["items"] if item["type"] == "personal"]
    assert len(set(personal)) == 65
    assert len(personal) == 65
    assert pages[0]["has_more"] is True and pages[0]["next_offset"] == 30
    assert pages[-1]["has_more"] is False and pages[-1]["next_offset"] is None
    oldest = personal[-1]
    assert client.get(f"{API}/notifications/{oldest}", headers=hdr(A)).status_code == 200
    assert client.get(f"{API}/notifications/{oldest}", headers=hdr(B)).status_code == 404
    assert client.get(f"{API}/notifications/n-999999", headers=hdr(A)).status_code == 404
    assert client.get(f"{API}/notifications?offset=-1", headers=hdr(A)).status_code == 422


def test_account_data_purge_removes_notification_preferences(client, fresh):
    from app.models.notification_model import NotificationPreference
    from app.repositories.db_user_repository import delete_user_data
    client.patch(f"{API}/notifications/preferences", headers=hdr(A), json={"announcements": False})
    assert fresh.get(NotificationPreference, A) is not None
    delete_user_data(fresh, A)
    fresh.commit()
    fresh.expire_all()
    assert fresh.get(NotificationPreference, A) is None


def test_favorite_without_profile_does_not_claim_personalized_season(client, fresh, monkeypatch):
    if fresh.query(Destination).filter_by(destination_id=DEST).first() is None:
        pytest.skip("Requires catalogue fixture")
    fresh.add(Favorite(user_id=A, destination_id=DEST))
    fresh.commit()
    def unexpected_calendar(*args, **kwargs):
        raise AssertionError("Personalized season must require a traveler profile")
    monkeypatch.setattr(notification_service.destination_context_service, "calendar", unexpected_calendar)
    assert all(item["kind"] != "mejor_mes" for item in feed(client, A)["items"])
