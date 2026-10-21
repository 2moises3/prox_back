"""
Recuperar contraseña por correo con código de 6 dígitos.

Usa EMAIL_BACKEND=memory (los correos quedan en email_service.OUTBOX) y crea usuarios
temporales (prefijo ZFGT) que elimina al terminar.
"""
import logging
import re
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.config.settings import get_settings
from fastapi.testclient import TestClient

from app.main import app
from app.config.database import SessionLocal
from app.core import rate_limit
from app.core.security import create_access_token
from app.models.notification_model import Notification
from app.models.password_reset_model import PasswordResetCode
from app.models.user_model import User
from app.services import email_service
from app.utils.hash_util import get_password_hash

API = "/api/v1"
OLD = "ClaveAnterior123"
NEW = "ClaveNuevaSegura456"
ACTIVE, OTHER, INACTIVE, DELETED = "ZFGT_ACTIVE", "ZFGT_OTHER", "ZFGT_INACTIVE", "ZFGT_DELETED"
EMAIL = lambda uid: f"{uid.lower()}@mailinator.com"
IDS = [ACTIVE, OTHER, INACTIVE, DELETED]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def entorno(monkeypatch):
    monkeypatch.setattr(email_service, "_backend", lambda: "memory")
    monkeypatch.setattr(get_settings(), "PASSWORD_RESET_BY_EMAIL", True)
    email_service.OUTBOX.clear()
    for lim in (rate_limit.login_failures, rate_limit.forgot_attempts, rate_limit.reset_attempts):
        lim.reset()
    db = SessionLocal()
    _purge(db)
    for uid, active, status in ((ACTIVE, True, "active"), (OTHER, True, "active"),
                                (INACTIVE, False, "disabled"), (DELETED, False, "deleted")):
        db.add(User(user_id=uid, name=f"Nombre {uid}", email=EMAIL(uid), password_hash=get_password_hash(OLD),
                    role="traveler", is_active=active, account_status=status))
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    _purge(db)
    db.close()
    for lim in (rate_limit.login_failures, rate_limit.forgot_attempts, rate_limit.reset_attempts):
        lim.reset()


def _purge(db):
    db.query(PasswordResetCode).filter(PasswordResetCode.user_id.in_(IDS)).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.user_id.in_(IDS)).delete(synchronize_session=False)
    db.query(User).filter(User.user_id.in_(IDS)).delete(synchronize_session=False)
    db.commit()


def forgot(client, uid_or_email):
    email = uid_or_email if "@" in uid_or_email else EMAIL(uid_or_email)
    return client.post(f"{API}/auth/forgot-password", json={"email": email})


def last_code(uid=ACTIVE):
    mails = [m for m in email_service.OUTBOX if m["to"] == EMAIL(uid)]
    assert mails, "no llegó ningún correo"
    return re.search(r"\b(\d{6})\b", mails[-1]["text"]).group(1)


def reset(client, code, uid=ACTIVE, new=NEW):
    return client.post(f"{API}/auth/reset-password", json={"email": EMAIL(uid), "code": code, "new_password": new})


def login(client, password, uid=ACTIVE):
    return client.post(f"{API}/auth/login", json={"email": EMAIL(uid), "password": password})


# ── Pedir el código ───────────────────────────────────────────────────────────

def test_llega_un_correo_con_codigo_de_6_digitos(client):
    r = forgot(client, ACTIVE)
    assert r.status_code == 200
    assert len(email_service.OUTBOX) == 1
    mail = email_service.OUTBOX[0]
    assert mail["to"] == EMAIL(ACTIVE) and "PROXVEL" in mail["subject"]
    assert re.search(r"\b\d{6}\b", mail["text"]) and "15 minutos" in mail["text"]


def test_la_respuesta_es_igual_exista_o_no_el_correo(client):
    existe = forgot(client, ACTIVE)
    no_existe = forgot(client, "nadie.registrado@mailinator.com")
    assert existe.status_code == no_existe.status_code == 200
    assert existe.json() == no_existe.json()
    assert len(email_service.OUTBOX) == 1  # solo el real


@pytest.mark.parametrize("uid", [INACTIVE, DELETED])
def test_cuentas_desactivadas_o_eliminadas_no_reciben_correo(client, uid):
    assert forgot(client, uid).status_code == 200
    assert email_service.OUTBOX == []


def test_el_correo_no_distingue_mayusculas(client):
    assert forgot(client, EMAIL(ACTIVE).upper()).status_code == 200
    assert len(email_service.OUTBOX) == 1


def test_correo_invalido_da_422(client):
    assert client.post(f"{API}/auth/forgot-password", json={"email": "no-es-correo"}).status_code == 422


def test_se_limita_por_correo_a_3_por_hora(client):
    for _ in range(3):
        assert forgot(client, ACTIVE).status_code == 200
    r = forgot(client, ACTIVE)
    assert r.status_code == 429 and "Retry-After" in r.headers
    assert forgot(client, OTHER).status_code == 200  # otro correo no se ve afectado


def test_se_limita_por_ip_a_10_por_hora(client):
    codes = [forgot(client, f"zfgt.ip{i}@mailinator.com").status_code for i in range(12)]
    assert codes[:10] == [200] * 10 and 429 in codes[10:]


def test_un_codigo_nuevo_invalida_el_anterior(client):
    forgot(client, ACTIVE)
    primero = last_code()
    forgot(client, ACTIVE)
    segundo = last_code()
    assert primero != segundo
    assert reset(client, primero).status_code == 400  # el viejo ya no sirve
    assert reset(client, segundo).status_code == 200


# ── Canjear el código ─────────────────────────────────────────────────────────

def test_flujo_completo_cambia_la_contrasena(client):
    forgot(client, ACTIVE)
    r = reset(client, last_code())
    assert r.status_code == 200
    assert login(client, OLD).status_code == 401
    assert login(client, NEW).status_code == 200


def test_el_codigo_sirve_una_sola_vez(client):
    forgot(client, ACTIVE)
    code = last_code()
    assert reset(client, code).status_code == 200
    assert reset(client, code, new="OtraClaveDistinta789").status_code == 400
    assert login(client, NEW).status_code == 200


def test_codigo_incorrecto_y_mensaje_generico(client):
    forgot(client, ACTIVE)
    r = reset(client, "000000" if last_code() != "000000" else "111111")
    assert r.status_code == 400
    assert r.json()["detail"] == "El código es incorrecto o ya venció."
    # Un correo inexistente recibe exactamente el mismo mensaje.
    r2 = client.post(f"{API}/auth/reset-password",
                     json={"email": "nadie@mailinator.com", "code": "123456", "new_password": NEW})
    assert r2.status_code == 400 and r2.json()["detail"] == r.json()["detail"]


def test_se_bloquea_tras_5_intentos_fallidos_incluso_con_el_codigo_correcto(client):
    forgot(client, ACTIVE)
    real = last_code()
    mal = "123456" if real != "123456" else "654321"
    for _ in range(4):
        assert reset(client, mal).status_code == 400
    r = reset(client, mal)  # el 5.º fallo quema el código
    assert r.status_code == 400 and "Pide un código nuevo" in r.json()["detail"]
    assert reset(client, real).status_code == 400
    assert login(client, OLD).status_code == 200  # la contraseña no cambió


def test_codigo_vencido_no_sirve(client):
    forgot(client, ACTIVE)
    code = last_code()
    db = SessionLocal()
    db.query(PasswordResetCode).filter_by(user_id=ACTIVE).update(
        {"expires_at": datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)})
    db.commit()
    db.close()
    assert reset(client, code).status_code == 400
    assert login(client, OLD).status_code == 200


def test_el_codigo_de_un_usuario_no_sirve_para_otro(client):
    forgot(client, ACTIVE)
    forgot(client, OTHER)
    code_a = last_code(ACTIVE)
    assert reset(client, code_a, uid=OTHER).status_code == 400
    assert login(client, OLD, uid=OTHER).status_code == 200


def test_validaciones_de_entrada(client):
    forgot(client, ACTIVE)
    code = last_code()
    r = reset(client, code, new="1234567")
    assert r.status_code == 422 and r.json()["detail"] == "La contraseña debe tener al menos 8 caracteres."
    r = reset(client, "12ab56")
    assert r.status_code == 422 and r.json()["detail"] == "El código debe tener 6 dígitos."
    assert login(client, OLD).status_code == 200


def test_adivinar_codigos_se_limita_por_correo(client):
    forgot(client, ACTIVE)
    mal = "123456" if last_code() != "123456" else "654321"
    codigos = [reset(client, mal).status_code for _ in range(12)]
    assert 429 in codigos


def test_restablecer_cierra_las_sesiones_abiertas_y_deja_aviso(client):
    viejo = create_access_token({"sub": ACTIVE})
    assert client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {viejo}"}).status_code == 200
    time.sleep(1.2)
    forgot(client, ACTIVE)
    assert reset(client, last_code()).status_code == 200
    assert client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {viejo}"}).status_code == 401

    token = login(client, NEW).json()["data"]["access_token"]
    items = client.get(f"{API}/notifications", headers={"Authorization": f"Bearer {token}"}).json()["data"]["items"]
    assert any(i["kind"] == "seguridad" for i in items)


# ── Sin filtraciones ──────────────────────────────────────────────────────────

def test_el_codigo_no_se_guarda_en_claro_ni_se_loguea(client, caplog):
    with caplog.at_level(logging.DEBUG):
        forgot(client, ACTIVE)
        code = last_code()
        reset(client, code)
    assert all(code not in r.getMessage() for r in caplog.records)
    db = SessionLocal()
    rows = db.query(PasswordResetCode).filter_by(user_id=ACTIVE).all()
    db.close()
    assert rows and all(code not in r.code_hash for r in rows) and all(len(r.code_hash) == 64 for r in rows)


def test_auditoria_registra_solicitud_y_exito(client, caplog):
    with caplog.at_level(logging.INFO, logger="proxvel.audit"):
        forgot(client, ACTIVE)
        reset(client, last_code())
    lines = [r.getMessage() for r in caplog.records if r.name == "proxvel.audit"]
    assert any("password_forgot REQUESTED" in l and f"user={ACTIVE}" in l for l in lines)
    assert any("password_reset OK" in l and f"user={ACTIVE}" in l for l in lines)


def test_contacto_de_soporte_es_publico(client):
    r = client.get(f"{API}/auth/support-contact")
    assert r.status_code == 200 and "support_email" in r.json()["data"]


def test_al_borrar_el_usuario_se_borran_sus_codigos(client):
    forgot(client, ACTIVE)
    db = SessionLocal()
    assert db.query(PasswordResetCode).filter_by(user_id=ACTIVE).count() == 1
    db.query(User).filter_by(user_id=ACTIVE).delete()
    db.commit()
    assert db.query(PasswordResetCode).filter_by(user_id=ACTIVE).count() == 0
    db.close()


def test_apagado_responde_503_con_soporte(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "PASSWORD_RESET_BY_EMAIL", False)
    r = client.post("/api/v1/auth/forgot-password", json={"email": "alguien@mailinator.com"})
    assert r.status_code == 503
    r = client.post("/api/v1/auth/reset-password",
                    json={"email": "alguien@mailinator.com", "code": "123456", "new_password": "ClaveNueva123"})
    assert r.status_code == 503
    info = client.get("/api/v1/auth/support-contact").json()["data"]
    assert info["password_reset_by_email"] is False
