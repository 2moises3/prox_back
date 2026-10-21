"""
Pruebas de seguridad: rutas protegidas, límite de intentos, token por rol,
configuración de producción y validaciones de entrada.

Crean usuarios temporales (prefijo ZSEC) y los eliminan al terminar.
"""
import base64
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.config.database import SessionLocal
from app.config.settings import Settings
from app.core import rate_limit
from app.core.security import create_access_token, decode_access_token, token_lifetime_for_role
from app.models.user_model import User
from app.utils.hash_util import get_password_hash

GOOD_PASSWORD = "ClaveSegura123"
USERS = {
    "traveler": ("ZSEC_TRAVELER", "zsec.traveler@mailinator.com"),
    "admin": ("ZSEC_ADMIN", "zsec.admin@mailinator.com"),
    "super_admin": ("ZSEC_SUPER", "zsec.super@mailinator.com"),
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def temp_users():
    db = SessionLocal()
    ids = [uid for uid, _ in USERS.values()]
    db.query(User).filter(User.user_id.in_(ids)).delete(synchronize_session=False)
    for role, (uid, email) in USERS.items():
        db.add(User(user_id=uid, name=uid, email=email, password_hash=get_password_hash(GOOD_PASSWORD),
                    role=role, is_active=True, account_status="active"))
    db.commit()
    yield
    db.query(User).filter(User.user_id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    db.close()


@pytest.fixture(autouse=True)
def clean_limiters():
    rate_limit.login_failures.reset()
    rate_limit.register_attempts.reset()
    yield
    rate_limit.login_failures.reset()
    rate_limit.register_attempts.reset()


def auth(role: str) -> dict:
    uid, _ = USERS[role]
    return {"Authorization": f"Bearer {create_access_token({'sub': uid})}"}


API = "/api/v1"

# ── Rutas que antes estaban abiertas ──────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "/reviews/pending",
    "/reviews/destination/machu_picchu",
    "/reviews/R00001",
    "/recommendations/contextual",
    "/recommendations/search",
    "/recommendations/base",
    "/data/status",
])
def test_rutas_exigen_autenticacion(client, path):
    assert client.get(API + path).status_code == 401


@pytest.mark.parametrize("path", [
    "/reviews/pending",
    "/recommendations/contextual",
    "/recommendations/search",
    "/recommendations/base",
    "/data/status",
])
def test_rutas_administrativas_rechazan_viajero(client, path):
    assert client.get(API + path, headers=auth("traveler")).status_code == 403


@pytest.mark.parametrize("path", ["/data/status", "/recommendations/base"])
def test_rutas_administrativas_aceptan_admin(client, path):
    assert client.get(API + path, headers=auth("admin")).status_code == 200


def test_users_demo_ya_no_es_publico(client):
    # Sin la ruta /users/demo, "demo" se interpreta como un user_id: exige sesión y ser ese usuario.
    assert client.get(API + "/users/demo").status_code == 401
    assert client.get(API + "/users/demo", headers=auth("traveler")).status_code == 403


def test_resena_ajena_no_se_puede_leer(client):
    r = client.get(API + "/reviews/R_NO_EXISTE", headers=auth("traveler"))
    assert r.status_code == 404


# ── Límite de intentos ────────────────────────────────────────────────────────

def test_login_se_bloquea_tras_cinco_fallos(client):
    email = USERS["traveler"][1]
    for _ in range(5):
        r = client.post(API + "/auth/login", json={"email": email, "password": "incorrecta"})
        assert r.status_code == 401
    r = client.post(API + "/auth/login", json={"email": email, "password": "incorrecta"})
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    # Bloqueado también con la contraseña correcta mientras dure la ventana.
    r = client.post(API + "/auth/login", json={"email": email, "password": GOOD_PASSWORD})
    assert r.status_code == 429


def test_login_correcto_reinicia_el_contador(client):
    email = USERS["traveler"][1]
    for _ in range(3):
        client.post(API + "/auth/login", json={"email": email, "password": "incorrecta"})
    assert client.post(API + "/auth/login", json={"email": email, "password": GOOD_PASSWORD}).status_code == 200
    for _ in range(4):
        assert client.post(API + "/auth/login", json={"email": email, "password": "incorrecta"}).status_code == 401


def test_bloqueo_de_un_correo_no_afecta_a_otro(client):
    for _ in range(5):
        client.post(API + "/auth/login", json={"email": USERS["traveler"][1], "password": "incorrecta"})
    r = client.post(API + "/auth/login", json={"email": USERS["admin"][1], "password": GOOD_PASSWORD})
    assert r.status_code == 200


def test_correo_inexistente_tambien_cuenta_fallos(client):
    for _ in range(5):
        assert client.post(API + "/auth/login", json={"email": "nadie@mailinator.com", "password": "x12345678"}).status_code == 401
    assert client.post(API + "/auth/login", json={"email": "nadie@mailinator.com", "password": "x12345678"}).status_code == 429


def test_registro_limitado_por_ip(client):
    codes = []
    for i in range(12):
        r = client.post(API + "/users", json={"email": f"zsec.reg{i}@mailinator.com", "password": "corta"})
        codes.append(r.status_code)
    assert 429 in codes
    assert codes.index(429) == 10  # los 10 primeros pasan el límite (y fallan por validación)


# ── Token ─────────────────────────────────────────────────────────────────────

def test_token_de_admin_dura_menos_que_el_de_viajero():
    admin = token_lifetime_for_role("admin")
    traveler = token_lifetime_for_role("traveler")
    assert token_lifetime_for_role("super_admin") == admin
    assert admin < traveler
    assert admin.total_seconds() <= 24 * 3600


def test_login_emite_token_con_expiracion_segun_rol(client):
    def lifetime(role):
        r = client.post(API + "/auth/login", json={"email": USERS[role][1], "password": GOOD_PASSWORD})
        assert r.status_code == 200
        payload = decode_access_token(r.json()["data"]["access_token"])
        return payload["exp"] - datetime.now(timezone.utc).timestamp()
    assert lifetime("admin") < lifetime("traveler")


# ── Entrada ───────────────────────────────────────────────────────────────────

def test_password_corta_da_mensaje_legible(client):
    r = client.post(API + "/users", json={"email": "zsec.nuevo@mailinator.com", "password": "1234567"})
    assert r.status_code == 422
    assert r.json()["detail"] == "La contraseña debe tener al menos 8 caracteres."


def test_avatar_rechaza_archivos_que_no_son_imagen(client):
    uid, _ = USERS["traveler"]
    r = client.post(f"{API}/users/{uid}/avatar", headers=auth("traveler"),
                    files={"file": ("x.png", b"esto no es una imagen", "image/png")})
    assert r.status_code == 400
    r = client.post(f"{API}/users/{uid}/avatar", headers=auth("traveler"),
                    files={"file": ("x.html", b"<script>alert(1)</script>", "text/html")})
    assert r.status_code == 400


def test_avatar_rechaza_archivos_demasiado_grandes(client):
    uid, _ = USERS["traveler"]
    png = base64.b64decode("iVBORw0KGgo=") + b"0" * (6 * 1024 * 1024)
    r = client.post(f"{API}/users/{uid}/avatar", headers=auth("traveler"),
                    files={"file": ("x.png", png, "image/png")})
    assert r.status_code == 413


def test_no_se_puede_tocar_el_avatar_de_otro(client):
    r = client.post(f"{API}/users/{USERS['admin'][0]}/avatar", headers=auth("traveler"),
                    files={"file": ("x.png", b"x", "image/png")})
    assert r.status_code == 403


def test_cabeceras_de_seguridad(client):
    r = client.get(API + "/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"


# ── Configuración de producción ───────────────────────────────────────────────

BASE = dict(_env_file=None, SECRET_KEY="k" * 40, DATABASE_URL="postgresql://u:p@h/db")
SMTP = dict(EMAIL_BACKEND="smtp", SMTP_HOST="smtp.ejemplo.com", SMTP_FROM="no-responder@proxvel.pe")


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    """Las pruebas de configuración no deben heredar las variables del contenedor (DEBUG=True, etc.)."""
    for var in ("APP_ENV", "DEBUG", "SQL_ECHO", "ENABLE_DOCS", "CORS_ORIGINS", "TRUST_PROXY_HEADERS", "DATABASE_URL"):
        monkeypatch.delenv(var, raising=False)


def make(**over):
    return Settings(**{**BASE, **over})


def test_produccion_rechaza_cors_abierto():
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        make(APP_ENV="production", CORS_ORIGINS="*")


def test_produccion_rechaza_debug():
    with pytest.raises(ValidationError, match="DEBUG"):
        make(APP_ENV="production", CORS_ORIGINS="https://panel.proxvel.pe", DEBUG=True)


def test_produccion_rechaza_secret_key_debil():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        make(APP_ENV="production", CORS_ORIGINS="https://panel.proxvel.pe", SECRET_KEY="corta" * 3)


def test_produccion_exige_base_de_datos():
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        make(APP_ENV="production", CORS_ORIGINS="https://panel.proxvel.pe", DATABASE_URL=None)


def test_produccion_valida_oculta_swagger_y_desarrollo_lo_muestra():
    prod = make(APP_ENV="production", CORS_ORIGINS="https://panel.proxvel.pe", **SMTP)
    assert prod.is_production and not prod.docs_enabled and not prod.DEBUG
    assert make(APP_ENV="production", CORS_ORIGINS="https://panel.proxvel.pe", ENABLE_DOCS=True, **SMTP).docs_enabled
    dev = make()
    assert not dev.is_production and dev.docs_enabled


def test_secret_key_muy_corta_siempre_se_rechaza():
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        make(SECRET_KEY="abc")


def test_valores_por_defecto_son_seguros():
    s = make()
    assert s.DEBUG is False and s.SQL_ECHO is False and s.TRUST_PROXY_HEADERS is False
    assert "*" not in s.CORS_ORIGINS


def test_produccion_exige_correo_real_si_la_recuperacion_esta_activa():
    on = dict(APP_ENV="production", CORS_ORIGINS="https://panel.proxvel.pe", PASSWORD_RESET_BY_EMAIL=True)
    with pytest.raises(ValidationError, match="EMAIL_BACKEND"):
        make(**on)  # console por defecto
    with pytest.raises(ValidationError, match="SMTP_HOST"):
        make(**on, EMAIL_BACKEND="smtp", SMTP_FROM="a@b.pe")
    make(**on, **SMTP)  # completo: arranca


def test_produccion_sin_recuperacion_por_correo_no_exige_smtp():
    # v1: la recuperación por correo está apagada y el backend arranca sin SMTP.
    s = make(APP_ENV="production", CORS_ORIGINS="https://panel.proxvel.pe")
    assert s.PASSWORD_RESET_BY_EMAIL is False
