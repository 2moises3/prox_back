"""
Pruebas del restablecimiento de contraseña por un super_admin:
permisos, contraseña temporal, cierre de sesiones abiertas y auditoría en el log.

Crean usuarios temporales (prefijo ZPWD) y los eliminan al terminar.
"""
import logging
import re
import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.config.database import SessionLocal
from app.config.settings import get_settings
from app.core import rate_limit
from app.core.security import create_access_token
from app.models.user_model import User
from app.services.user_admin_service import generate_temporary_password
from app.utils.hash_util import get_password_hash

OLD_PASSWORD = "ClaveAnterior123"
API = "/api/v1"
SUPER, ADMIN, TARGET, DELETED, OTHER = "ZPWD_SUPER", "ZPWD_ADMIN", "ZPWD_TARGET", "ZPWD_DELETED", "ZPWD_OTHER"
EMAIL = lambda uid: f"{uid.lower()}@mailinator.com"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def temp_users():
    db = SessionLocal()
    ids = [SUPER, ADMIN, TARGET, DELETED, OTHER]
    db.query(User).filter(User.user_id.in_(ids)).delete(synchronize_session=False)
    for uid, role, status in ((SUPER, "super_admin", "active"), (ADMIN, "admin", "active"),
                              (TARGET, "traveler", "active"), (OTHER, "traveler", "active"),
                              (DELETED, "traveler", "deleted")):
        db.add(User(user_id=uid, name=uid, email=EMAIL(uid), password_hash=get_password_hash(OLD_PASSWORD),
                    role=role, is_active=(status == "active"), account_status=status))
    db.commit()
    yield
    db.query(User).filter(User.user_id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    db.close()


@pytest.fixture(autouse=True)
def clean_limiters():
    rate_limit.login_failures.reset()
    yield
    rate_limit.login_failures.reset()


def headers(uid: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token({'sub': uid})}"}


def reset(client, target, as_user=SUPER):
    return client.post(f"{API}/admin/users/{target}/reset-password", headers=headers(as_user))


def login(client, uid, password):
    return client.post(f"{API}/auth/login", json={"email": EMAIL(uid), "password": password})


# ── Generador ─────────────────────────────────────────────────────────────────

def test_generador_cumple_requisitos():
    seen = set()
    for _ in range(200):
        p = generate_temporary_password()
        assert len(p) == 12
        assert re.search(r"[A-Z]", p) and re.search(r"[a-z]", p) and re.search(r"\d", p)
        assert not re.search(r"[0OIl1]", p)  # sin caracteres ambiguos
        seen.add(p)
    assert len(seen) == 200  # no se repiten


# ── Permisos ──────────────────────────────────────────────────────────────────

def test_solo_super_admin_puede_restablecer(client):
    assert client.post(f"{API}/admin/users/{TARGET}/reset-password").status_code == 401
    assert reset(client, TARGET, as_user=OTHER).status_code == 403   # viajero
    assert reset(client, TARGET, as_user=ADMIN).status_code == 403   # admin normal


def test_guardas_de_negocio(client):
    assert reset(client, SUPER).status_code == 400             # a sí mismo
    assert reset(client, "NO_EXISTE").status_code == 404
    assert reset(client, "ANON_DELETED").status_code == 400    # cuenta de sistema
    assert reset(client, DELETED).status_code == 400           # eliminado


# ── Flujo completo ────────────────────────────────────────────────────────────

def test_restablecer_devuelve_temporal_una_vez_y_cambia_la_clave(client):
    r = reset(client, TARGET)
    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "no-store"
    data = r.json()["data"]
    temp = data["temporary_password"]
    assert data["user_id"] == TARGET and data["email"] == EMAIL(TARGET)
    assert len(temp) == 12 and data["sessions_invalidated"] is True

    assert login(client, TARGET, OLD_PASSWORD).status_code == 401   # la anterior ya no sirve
    assert login(client, TARGET, temp).status_code == 200           # la temporal sí

    # No hay forma de volver a consultarla: ni en los listados ni en el detalle.
    for path in ("/admin/users", f"/admin/users/{TARGET}/details"):
        body = client.get(API + path, headers=headers(SUPER)).text
        assert temp not in body


def test_cada_restablecimiento_genera_una_clave_distinta(client):
    a = reset(client, TARGET).json()["data"]["temporary_password"]
    b = reset(client, TARGET).json()["data"]["temporary_password"]
    assert a != b


def test_sesiones_abiertas_se_cierran_al_restablecer(client):
    old_token = create_access_token({"sub": OTHER})
    assert client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {old_token}"}).status_code == 200

    time.sleep(1.2)  # el claim iat tiene resolución de segundos
    temp = reset(client, OTHER).json()["data"]["temporary_password"]

    r = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {old_token}"})
    assert r.status_code == 401
    assert "sesión expiró" in r.json()["detail"]

    # Un token emitido por el login nuevo sí funciona.
    new_token = login(client, OTHER, temp).json()["data"]["access_token"]
    assert client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {new_token}"}).status_code == 200


def test_token_sin_iat_se_rechaza_tras_un_restablecimiento(client):
    s = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(hours=1)
    legacy = jwt.encode({"sub": OTHER, "exp": expires}, s.SECRET_KEY, algorithm=s.ALGORITHM)  # token antiguo, sin iat
    assert client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {legacy}"}).status_code == 401


def test_usuario_sin_restablecimiento_no_se_ve_afectado(client):
    assert client.get(f"{API}/auth/me", headers=headers(ADMIN)).status_code == 200


def test_la_fecha_interna_no_sale_en_las_respuestas(client):
    r = client.get(f"{API}/auth/me", headers=headers(TARGET))
    assert r.status_code == 200
    assert "password_changed_at" not in r.text and "password_hash" not in r.text


# ── Auditoría ─────────────────────────────────────────────────────────────────

def test_auditoria_registra_quien_a_quien_y_nunca_la_clave(client, caplog):
    with caplog.at_level(logging.INFO, logger="proxvel.audit"):
        ok = reset(client, TARGET)
        reset(client, "NO_EXISTE")
    temp = ok.json()["data"]["temporary_password"]
    lines = [r.getMessage() for r in caplog.records if r.name == "proxvel.audit"]

    ok_line = next(l for l in lines if "password_reset OK" in l)
    assert f"actor={SUPER}" in ok_line and f"target={TARGET}" in ok_line and "ip=" in ok_line
    assert any("password_reset DENIED" in l and "target=NO_EXISTE" in l for l in lines)
    assert all(temp not in l for l in lines)           # la clave jamás se escribe
    assert all(temp not in r.getMessage() for r in caplog.records)
