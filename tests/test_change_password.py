"""
Pruebas de POST /auth/change-password: exige la contraseña actual, mínimo 8 caracteres,
cierra las demás sesiones, devuelve un token nuevo y deja auditoría sin la contraseña.

Crean usuarios temporales (prefijo ZCHG) y los eliminan al terminar.
"""
import logging
import time

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config.database import SessionLocal
from app.core import rate_limit
from app.core.security import create_access_token
from app.models.user_model import User
from app.utils.hash_util import get_password_hash

API = "/api/v1"
OLD = "ClaveAnterior123"
NEW = "ClaveNuevaSegura456"
USER, OTHER = "ZCHG_USER", "ZCHG_OTHER"
EMAIL = lambda uid: f"{uid.lower()}@mailinator.com"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def fresh_user():
    """Cada prueba parte de un usuario con la contraseña original y sin marca de cambio."""
    rate_limit.login_failures.reset()
    db = SessionLocal()
    db.query(User).filter(User.user_id.in_([USER, OTHER])).delete(synchronize_session=False)
    for uid in (USER, OTHER):
        db.add(User(user_id=uid, name=uid, email=EMAIL(uid), password_hash=get_password_hash(OLD),
                    role="traveler", is_active=True, account_status="active"))
    db.commit()
    db.close()
    yield
    rate_limit.login_failures.reset()
    db = SessionLocal()
    db.query(User).filter(User.user_id.in_([USER, OTHER])).delete(synchronize_session=False)
    db.commit()
    db.close()


def hdr(token=None, uid=USER):
    return {"Authorization": f"Bearer {token or create_access_token({'sub': uid})}"}


def change(client, current, new, headers=None):
    return client.post(f"{API}/auth/change-password", headers=headers or hdr(),
                       json={"current_password": current, "new_password": new})


def login(client, password, uid=USER):
    return client.post(f"{API}/auth/login", json={"email": EMAIL(uid), "password": password})


def test_requiere_sesion(client):
    r = client.post(f"{API}/auth/change-password", json={"current_password": OLD, "new_password": NEW})
    assert r.status_code == 401


def test_cambio_correcto(client):
    r = change(client, OLD, NEW)
    assert r.status_code == 200
    assert r.json()["data"]["token_type"] == "bearer"
    assert login(client, OLD).status_code == 401   # la anterior ya no sirve
    assert login(client, NEW).status_code == 200   # la nueva sí


def test_contrasena_actual_incorrecta_se_rechaza_con_400(client):
    r = change(client, "no-es-la-actual", NEW)
    assert r.status_code == 400                    # 400, no 401: la app no debe cerrar la sesión
    assert r.json()["detail"] == "La contraseña actual no es correcta."
    assert login(client, OLD).status_code == 200   # no cambió nada


def test_minimo_8_caracteres(client):
    r = change(client, OLD, "1234567")
    assert r.status_code == 422
    assert r.json()["detail"] == "La contraseña debe tener al menos 8 caracteres."
    assert login(client, OLD).status_code == 200


def test_la_nueva_debe_ser_distinta(client):
    r = change(client, OLD, OLD)
    assert r.status_code == 400
    assert "distinta" in r.json()["detail"]


def test_devuelve_token_nuevo_y_cierra_las_otras_sesiones(client):
    viejo = create_access_token({"sub": USER})
    assert client.get(f"{API}/auth/me", headers=hdr(viejo)).status_code == 200
    time.sleep(1.2)  # el claim iat tiene resolución de segundos

    r = change(client, OLD, NEW, headers=hdr(viejo))
    assert r.status_code == 200
    nuevo = r.json()["data"]["access_token"]

    assert client.get(f"{API}/auth/me", headers=hdr(viejo)).status_code == 401   # otra sesión: cerrada
    assert client.get(f"{API}/auth/me", headers=hdr(nuevo)).status_code == 200   # este dispositivo sigue conectado


def test_no_afecta_a_otros_usuarios(client):
    change(client, OLD, NEW)
    assert login(client, OLD, uid=OTHER).status_code == 200


def test_intentos_fallidos_se_bloquean_como_en_el_login(client):
    for _ in range(5):
        assert change(client, "incorrecta", NEW).status_code == 400
    r = change(client, OLD, NEW)  # ya bloqueado: ni con la actual correcta
    assert r.status_code == 429
    assert "Retry-After" in r.headers


def test_el_perfil_ya_no_permite_cambiar_la_contrasena_sin_la_actual(client):
    """PATCH /users/{id} ignora `password`: antes bastaba un token robado para cambiarla."""
    r = client.patch(f"{API}/users/{USER}", headers=hdr(), json={"name": "Nuevo Nombre", "password": NEW})
    assert r.status_code == 200
    assert login(client, OLD).status_code == 200
    assert login(client, NEW).status_code == 401


def test_auditoria_registra_el_cambio_y_nunca_las_contrasenas(client, caplog):
    with caplog.at_level(logging.INFO, logger="proxvel.audit"):
        change(client, "incorrecta", NEW)
        change(client, OLD, NEW)
    lines = [r.getMessage() for r in caplog.records if r.name == "proxvel.audit"]
    assert any("password_change DENIED" in l and f"user={USER}" in l and "ip=" in l for l in lines)
    assert any("password_change OK" in l and f"user={USER}" in l for l in lines)
    for secret in (OLD, NEW, "incorrecta"):
        assert all(secret not in r.getMessage() for r in caplog.records)
