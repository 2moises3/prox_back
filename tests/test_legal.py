"""
Etapa legal: consentimiento registrado, eliminación de cuenta por el propio viajero (con borrado
completo), cerrar sesión en todos los dispositivos, reportes/ocultamiento de reseñas y auditoría.
Necesita los datos de `python scripts/seed_from_thesis.py`; si la BD está vacía se omite.
"""
import uuid
import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.config.database import SessionLocal
from app.core import rate_limit
from app.core.audit import purge_audit, AuditDBHandler
from app.core.legal import TERMS_VERSION
from app.core.security import create_access_token
from app.models.archive_model import Archive
from app.models.audit_event_model import AuditEvent
from app.models.destination_model import Destination
from app.models.notification_model import Notification
from app.models.review_model import Review
from app.models.review_report_model import ReviewReport
from app.models.traveler_profile_model import TravelerProfile
from app.models.user_model import User
from app.services import user_admin_service
from app.utils.hash_util import get_password_hash

API = "/api/v1"
PWD = "ClaveSegura123"
DEST = "chan_chan"
A, B, ADM = "ZLEG_A", "ZLEG_B", "ZLEG_ADM"
EMAIL_NEW = "zleg.nuevo@mailinator.com"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _purge(db):
    ids = [A, B, ADM]
    ids += [u for (u,) in db.query(User.user_id).filter(User.email.like("zleg.%")).all()]
    ids += [u for (u,) in db.query(User.user_id).filter(User.email.like("%@deleted.local"), User.name == "Usuario eliminado").all()
            if u.startswith("U")]
    ids = list(dict.fromkeys(ids))
    db.execute(text("delete from review_reports where reporter_user_id = any(:i)"), {"i": ids})
    db.execute(text("delete from reviews where user_id = any(:i) or review_id like 'zleg-%'"), {"i": ids})
    tablas = [t for (t,) in db.execute(text(
        "select table_name from information_schema.columns where column_name='user_id' "
        "and table_schema='public' and table_name not in ('users','audit_events')"))]
    for t in tablas:
        db.execute(text(f'delete from "{t}" where user_id = any(:i)'), {"i": ids})
    db.execute(text("delete from audit_events where user_id = any(:i)"), {"i": ids})
    db.execute(text("delete from users where user_id = any(:i)"), {"i": ids})
    db.commit()


@pytest.fixture(scope="module", autouse=True)
def entorno():
    db = SessionLocal()
    seeded = False
    if os.getenv("PROXVEL_ISOLATED_LEGAL_TEST") == "1":
        assert db.bind.url.database.startswith("proxvel_legal_test_")
        assert db.query(Destination).filter_by(destination_id=DEST).first() is None
        db.add(Destination(destination_id=DEST, destination="Chan Chan (fixture)", in_engine=False))
        db.commit()
        seeded = True
    if db.query(Destination).filter_by(destination_id=DEST).first() is None:
        db.close()
        pytest.skip("BD sin datos: ejecuta scripts/seed_from_thesis.py")
    _purge(db)
    for uid, role in ((A, "traveler"), (B, "traveler"), (ADM, "admin")):
        db.add(User(user_id=uid, name=f"Ana {uid}" if uid == A else uid, email=f"{uid.lower().replace('_', '.')}@mailinator.com",
                    password_hash=get_password_hash(PWD), role=role, is_active=True, account_status="active",
                    residence_department="LIMA", residence_province="LIMA", residence_city="MIRAFLORES"))
    db.commit()
    yield
    db.expire_all()
    _purge(db)
    if seeded:
        db.query(Destination).filter_by(destination_id=DEST).delete()
        db.commit()
    db.close()


@pytest.fixture(autouse=True)
def limites():
    for lim in (rate_limit.login_failures, rate_limit.register_attempts):
        lim.reset()


def h(uid, role="traveler"):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': uid, 'role': role})}"}


def login(client, email, pwd=PWD):
    return client.post(f"{API}/auth/login", json={"email": email, "password": pwd})


# ── Consentimiento ────────────────────────────────────────────────────────────

def test_registro_exige_aceptar_y_guarda_version(client):
    body = {"name": "Nuevo Viajero", "email": EMAIL_NEW, "password": "ClaveSegura123"}
    assert client.post(f"{API}/users", json=body).status_code == 422
    assert client.post(f"{API}/users", json={**body, "accepted_terms": False}).status_code == 422
    r = client.post(f"{API}/users", json={**body, "accepted_terms": True})
    assert r.status_code == 201, r.text
    data = r.json()["data"]
    assert data["accepted_terms_version"] == TERMS_VERSION
    assert data["accepted_terms_at"]


def test_usuario_existente_acepta_la_version_vigente(client):
    me = client.get(f"{API}/auth/me", headers=h(A)).json()["data"]
    assert me["accepted_terms_version"] is None
    r = client.post(f"{API}/users/me/accept-terms", headers=h(A))
    assert r.status_code == 200
    assert r.json()["data"]["accepted_terms_version"] == TERMS_VERSION
    assert client.post(f"{API}/users/me/accept-terms").status_code == 401


# ── Cerrar sesión en todos los dispositivos ───────────────────────────────────

def test_cerrar_sesion_en_todos_los_dispositivos(client):
    token = login(client, "zleg.b@mailinator.com").json()["data"]["access_token"]
    hdr = {"Authorization": f"Bearer {token}"}
    assert client.get(f"{API}/auth/me", headers=hdr).status_code == 200
    import time
    time.sleep(1.1)  # el token se emite con precisión de segundos
    assert client.post(f"{API}/auth/logout-all", headers=hdr).status_code == 200
    assert client.get(f"{API}/auth/me", headers=hdr).status_code == 401
    # Puede volver a entrar
    time.sleep(1.1)
    assert login(client, "zleg.b@mailinator.com").status_code == 200


# ── Reportes y ocultamiento de reseñas ────────────────────────────────────────

def _review(db, uid, rid, text_="Reseña de prueba legal"):
    db.add(Review(review_id=rid, user_id=uid, destination_id=DEST, rating_general=4.0, review_text=text_,
                  status="pending_processing", processing_month="2026-10"))
    db.commit()


def test_reportar_y_ocultar_resena(client):
    with SessionLocal() as db:
        _review(db, A, "zleg-r1")
    # No se reporta la propia ni con motivo inválido; sí la ajena, una sola vez.
    assert client.post(f"{API}/reviews/zleg-r1/report", json={"reason": "spam"}, headers=h(A)).status_code == 409
    assert client.post(f"{API}/reviews/zleg-r1/report", json={"reason": "xx"}, headers=h(B)).status_code == 422
    assert client.post(f"{API}/reviews/zleg-r1/report", json={"reason": "ofensiva"}, headers=h(B)).status_code == 200
    assert client.post(f"{API}/reviews/zleg-r1/report", json={"reason": "ofensiva"}, headers=h(B)).status_code == 200
    assert client.post(f"{API}/reviews/no-existe/report", json={"reason": "spam"}, headers=h(B)).status_code == 404
    with SessionLocal() as db:
        assert db.query(ReviewReport).filter_by(review_id="zleg-r1").count() == 1

    # El equipo la ve marcada; el viajero ve la reseña sin datos internos.
    admin_list = client.get(f"{API}/reviews/destination/{DEST}", headers=h(ADM, "admin")).json()["data"]
    mine = next(r for r in admin_list if r["review_id"] == "zleg-r1")
    assert mine["report_count"] == 1 and mine["user_id"] == A
    pub = client.get(f"{API}/reviews/destination/{DEST}", headers=h(B)).json()["data"]
    row = next(r for r in pub if r["review_id"] == "zleg-r1")
    assert "user_id" not in row and "status" not in row and row["author_name"] == "Ana Z."

    # Ocultar: sale del listado público y vuelve al mostrar.
    assert client.patch(f"{API}/reviews/zleg-r1/hidden", json={"hidden": True}, headers=h(B)).status_code in (401, 403)
    assert client.patch(f"{API}/reviews/zleg-r1/hidden", json={"hidden": True}, headers=h(ADM, "admin")).status_code == 200
    pub = client.get(f"{API}/reviews/destination/{DEST}", headers=h(B)).json()["data"]
    assert "zleg-r1" not in {r["review_id"] for r in pub}
    adm = client.get(f"{API}/reviews/destination/{DEST}", headers=h(ADM, "admin")).json()["data"]
    assert next(r for r in adm if r["review_id"] == "zleg-r1")["is_hidden"] is True
    client.patch(f"{API}/reviews/zleg-r1/hidden", json={"hidden": False}, headers=h(ADM, "admin"))
    pub = client.get(f"{API}/reviews/destination/{DEST}", headers=h(B)).json()["data"]
    assert "zleg-r1" in {r["review_id"] for r in pub}


# ── Eliminación de cuenta por el propio viajero ───────────────────────────────

def test_eliminar_mi_cuenta_exige_contrasena_y_bloquea_acceso(client):
    assert client.get(f"{API}/users/me/deletion-policy").status_code == 401
    policy = client.get(f"{API}/users/me/deletion-policy", headers=h(A))
    assert policy.status_code == 200
    assert policy.json()["data"]["grace_days"] == 14
    assert client.post(f"{API}/users/me/delete-account", json={"password": "incorrecta"}, headers=h(A)).status_code == 403
    assert client.post(f"{API}/users/me/delete-account", json={"password": PWD}, headers=h(ADM, "admin")).status_code == 403
    r = client.post(f"{API}/users/me/delete-account", json={"password": PWD}, headers=h(A))
    assert r.status_code == 200, r.text
    assert r.json()["data"]["grace_days"] == 14
    assert login(client, "zleg.a@mailinator.com").status_code == 403, "acceso bloqueado al instante"
    assert client.get(f"{API}/auth/me", headers=h(A)).status_code == 403
    assert client.post(f"{API}/users/me/delete-account", json={"password": PWD}, headers=h(A)).status_code in (403, 409)


def test_borrado_completo_al_vencer_la_gracia(client, monkeypatch):
    # Datos de la cuenta que se va a borrar (A ya pidió la eliminación en la prueba anterior).
    with SessionLocal() as db:
        db.add(Archive(user_id=A, destination_id=DEST))
        db.add(Notification(user_id=A, kind="seguridad", title="t", body="b", dedupe_key=f"zleg-{uuid.uuid4().hex[:6]}"))
        db.add(TravelerProfile(user_id=A, intereses=["cultura"], clima_preferido="seco", tolerancia_multitudes="baja"))
        db.query(User).filter_by(user_id=A).update({
            "deletion_scheduled_at": datetime.utcnow() - timedelta(days=1),
            "avatar_url": "https://res.cloudinary.com/demo/image/upload/v1/proxvel/avatars/u/abc.jpg",
        })
        db.commit()

    borradas = []
    from app.services import cloudinary_service
    monkeypatch.setattr(cloudinary_service, "delete_image_by_url", lambda url: borradas.append(url) or True)

    result, error, _ = user_admin_service.process_due_deletions()
    assert error is None and result["processed"] >= 1

    with SessionLocal() as db:
        u = db.query(User).filter_by(user_id=A).first()
        assert u.account_status == "deleted" and u.name == "Usuario eliminado"
        assert u.email.endswith("@deleted.local")
        assert (u.residence_department, u.residence_province, u.residence_city) == (None, None, None)
        assert u.avatar_url is None and u.accepted_terms_at is None
        assert db.query(Archive).filter_by(user_id=A).count() == 0
        assert db.query(Notification).filter_by(user_id=A).count() == 0
        assert db.query(TravelerProfile).filter_by(user_id=A).count() == 0
        # Las reseñas se conservan, ya sin identificar a la persona.
        assert db.query(Review).filter_by(review_id="zleg-r1", user_id="ANON_DELETED").count() == 1
    assert borradas and "abc.jpg" in borradas[0], "la foto se borra también del servicio de imágenes"


def test_cloudinary_public_id_desde_url():
    captured = []
    from app.services import cloudinary_service as cs
    original = cs.delete_image
    cs.delete_image = lambda pid: captured.append(pid) or True
    try:
        cs.delete_image_by_url("https://res.cloudinary.com/x/image/upload/v1699/proxvel/avatars/U1/ab12cd.jpg")
        cs.delete_image_by_url("https://res.cloudinary.com/x/image/upload/proxvel/a/b.png?x=1")
        assert cs.delete_image_by_url(None) is False and cs.delete_image_by_url("https://otro.com/a.jpg") is False
    finally:
        cs.delete_image = original
    assert captured == ["proxvel/avatars/U1/ab12cd", "proxvel/a/b"]


# ── Auditoría con borrado a los 90 días ───────────────────────────────────────

def test_auditoria_guarda_eventos_y_purga(client):
    import logging
    logging.getLogger("proxvel.audit").info("AUDIT zleg_evento user=%s ip=%s", "ZLEG_X", "10.0.0.9")
    login(client, "zleg.b@mailinator.com", "mala-contrasena")  # genera AUDIT login FAILED
    with SessionLocal() as db:
        ev = db.query(AuditEvent).filter_by(user_id="ZLEG_X").first()
        assert ev and ev.ip == "10.0.0.9" and ev.event == "zleg_evento"
        assert db.query(AuditEvent).filter_by(user_id="ZLEG_B").count() >= 1
        db.query(AuditEvent).filter_by(user_id="ZLEG_X").update({"created_at": datetime.utcnow() - timedelta(days=91)})
        db.add(AuditEvent(event="reciente", user_id="ZLEG_X2", ip="1.1.1.1", message="AUDIT reciente"))
        db.commit()
    assert purge_audit(90) >= 1
    with SessionLocal() as db:
        assert db.query(AuditEvent).filter_by(user_id="ZLEG_X").count() == 0, "pasados 90 días se borra"
        assert db.query(AuditEvent).filter_by(user_id="ZLEG_X2").count() == 1
        db.query(AuditEvent).filter(AuditEvent.user_id.like("ZLEG%")).delete(synchronize_session=False)
        db.commit()
    assert any(isinstance(hd, AuditDBHandler) for hd in logging.getLogger("proxvel.audit").handlers)
