"""
Controles del dashboard: parámetros del motor, participación de destinos, edición de la ficha
comercial y versiones de la APK. Restaura todo lo que modifica.
Necesita los datos de `python scripts/seed_from_thesis.py`; si la BD está vacía se omite.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config.database import SessionLocal
from app.core.security import create_access_token
from app.models.app_release_model import AppRelease
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.user_model import User
from app.services import content_seed_service
from app.utils.hash_util import get_password_hash

API = "/api/v1"
ADMIN = "ZCTRL_ADMIN"
SUPER = "ZCTRL_SUPER"
DEST = "huaca_luna"
VERSION_CODES = (990001, 990002)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def entorno(client):
    db = SessionLocal()
    if db.query(Destination).filter_by(destination_id=DEST).first() is None:
        db.close()
        pytest.skip("BD sin datos: ejecuta scripts/seed_from_thesis.py")
    for uid, role in ((ADMIN, "admin"), (SUPER, "super_admin")):
        db.query(User).filter_by(user_id=uid).delete()
        db.add(User(user_id=uid, name=uid, email=f"{uid.lower()}@mailinator.com",
                    password_hash=get_password_hash("ClaveSegura123"), role=role,
                    is_active=True, account_status="active"))
    db.commit()
    config_original = client.get(f"{API}/admin/engine", headers=hs()).json()["data"]["config"]
    cat = db.query(TourismCatalog).filter_by(destination_id=DEST).first()
    ficha_original = {f: getattr(cat, f) for f in (*content_seed_service.CONTENT_FIELDS, "cost_level")}
    in_engine_original = db.query(Destination).filter_by(destination_id=DEST).first().in_engine
    yield
    db.expire_all()  # la API cambió datos en otras sesiones: releer antes de restaurar
    client.put(f"{API}/admin/engine/config", json={k: config_original[k] for k in ("alpha_absa", "beta_contexto", "w_clima", "w_aforo")}, headers=hs())
    cat = db.query(TourismCatalog).filter_by(destination_id=DEST).first()
    for f, v in ficha_original.items():
        setattr(cat, f, v)
    db.query(Destination).filter_by(destination_id=DEST).first().in_engine = in_engine_original
    db.query(AppRelease).filter(AppRelease.version_code.in_(VERSION_CODES)).delete(synchronize_session=False)
    for uid in (ADMIN, SUPER):
        db.query(User).filter_by(user_id=uid).delete()
    db.commit()
    db.close()


def ha():
    return {"Authorization": f"Bearer {create_access_token(data={'sub': ADMIN, 'role': 'admin'})}"}


def hs():
    return {"Authorization": f"Bearer {create_access_token(data={'sub': SUPER, 'role': 'super_admin'})}"}


# ── Motor ─────────────────────────────────────────────────────────────────────

def test_estado_del_motor(client):
    data = client.get(f"{API}/admin/engine", headers=ha()).json()["data"]
    assert data["defaults"] == {"alpha_absa": 0.25, "beta_contexto": 0.30, "w_clima": 0.5, "w_aforo": 0.5}
    assert data["counts"]["in_engine"] >= 1
    assert data["counts"]["total"] == len(data["destinations"])


def test_parametros_solo_super_admin_y_validados(client):
    nuevo = {"alpha_absa": 0.4, "beta_contexto": 0.2, "w_clima": 0.7, "w_aforo": 0.3}
    assert client.put(f"{API}/admin/engine/config", json=nuevo, headers=ha()).status_code == 403
    assert client.put(f"{API}/admin/engine/config", json={**nuevo, "w_aforo": 0.5}, headers=hs()).status_code == 422
    assert client.put(f"{API}/admin/engine/config", json={**nuevo, "alpha_absa": 1.5}, headers=hs()).status_code == 422
    r = client.put(f"{API}/admin/engine/config", json=nuevo, headers=hs())
    assert r.status_code == 200
    assert r.json()["data"]["config"]["alpha_absa"] == 0.4
    r = client.post(f"{API}/admin/engine/config/reset", headers=hs())
    assert r.json()["data"]["config"]["alpha_absa"] == 0.25


def test_sacar_y_volver_a_meter_destino_del_motor(client, monkeypatch):
    r = client.patch(f"{API}/admin/engine/destinations/{DEST}", json={"in_engine": False}, headers=ha())
    assert r.status_code == 200
    ids = [d["destination_id"] for d in client.get(f"{API}/admin/engine", headers=ha()).json()["data"]["destinations"] if d["in_engine"]]
    assert DEST not in ids
    assert client.patch(f"{API}/admin/engine/destinations/{DEST}", json={"in_engine": True}, headers=ha()).status_code == 200
    assert client.patch(f"{API}/admin/engine/destinations/no_existe", json={"in_engine": True}, headers=ha()).status_code == 404


# ── Ficha comercial del destino ───────────────────────────────────────────────

def test_editar_ficha_comercial(client):
    payload = {"recommended_duration": "2 horas", "difficulty": "Fácil", "cost_level": "medio",
               "altitude_m": 61, "how_to_get": "Taxi desde Trujillo"}
    r = client.patch(f"{API}/admin/destinations/{DEST}", json=payload, headers=ha())
    assert r.status_code == 200, r.text
    info = client.get(f"{API}/destinations/{DEST}").json()["data"]
    assert info["tourism_info"]["recommended_duration"] == "2 horas"
    assert info["tourism_info"]["difficulty"] == "facil"
    assert info["tourism_info"]["altitude_m"] == 61
    assert info["cost_level"] == "medio"


def test_ficha_valida_dificultad_y_costo(client):
    assert client.patch(f"{API}/admin/destinations/{DEST}", json={"difficulty": "extrema"}, headers=ha()).status_code == 422
    assert client.patch(f"{API}/admin/destinations/{DEST}", json={"cost_level": "gratis"}, headers=ha()).status_code == 422


def test_ficha_vacio_borra_costo_y_dificultad(client):
    client.patch(f"{API}/admin/destinations/{DEST}", json={"cost_level": "", "difficulty": ""}, headers=ha())
    info = client.get(f"{API}/destinations/{DEST}").json()["data"]
    assert info["cost_level"] is None
    assert info["tourism_info"]["difficulty"] is None


def test_viajero_no_edita_destinos(client):
    tok = create_access_token(data={"sub": "nadie", "role": "traveler"})
    r = client.patch(f"{API}/admin/destinations/{DEST}", json={"city": "X"}, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code in (401, 403)


# ── Versiones de la APK ───────────────────────────────────────────────────────

def _release(client, code, url="https://github.com/proxvel/app.apk", headers=None):
    return client.post(f"{API}/admin/releases", data={
        "version_name": f"1.0.{code % 10}", "version_code": str(code), "apk_url": url,
    }, headers=headers or hs())


def test_version_solo_super_admin_y_https(client):
    assert _release(client, VERSION_CODES[0], headers=ha()).status_code == 403
    assert _release(client, VERSION_CODES[0], url="http://inseguro.com/app.apk").status_code == 422
    assert _release(client, VERSION_CODES[0], url="javascript:alert(1)").status_code == 422


def test_publicar_version_y_ultima_publica(client):
    r1 = _release(client, VERSION_CODES[0])
    assert r1.status_code == 201, r1.text
    assert _release(client, VERSION_CODES[0]).status_code == 422, "código de versión repetido"
    r2 = _release(client, VERSION_CODES[1])
    id1, id2 = r1.json()["data"]["id"], r2.json()["data"]["id"]

    client.patch(f"{API}/admin/releases/{id1}/publish", json={"is_published": True}, headers=hs())
    client.patch(f"{API}/admin/releases/{id2}/publish", json={"is_published": True}, headers=hs())
    latest = client.get(f"{API}/releases/latest").json()["data"]
    assert latest["version_code"] == VERSION_CODES[1]
    assert "file_public_id" not in latest and "created_by" not in latest
    lista = {r["id"]: r for r in client.get(f"{API}/admin/releases", headers=ha()).json()["data"]}
    assert lista[id1]["is_published"] is False, "solo una versión publicada por plataforma"

    assert client.delete(f"{API}/admin/releases/{id2}", headers=hs()).status_code == 200
    assert client.get(f"{API}/releases/latest").json()["data"] is None or \
        client.get(f"{API}/releases/latest").json()["data"]["id"] != id2


# ── Inicio del dashboard: actividad y prioridades reales ─────────────────────

def test_actividad_reciente_y_prioridades(client):
    r = client.get(f"{API}/admin/metrics/activity", params={"limit": 5}, headers=ha())
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) <= 5
    fechas = [i["at"] for i in items]
    assert fechas == sorted(fechas, reverse=True), "de lo más nuevo a lo más viejo"
    for i in items:
        assert i["type"] in {"user", "review", "media", "announcement", "release"}
        assert i["link"].startswith("/")
    p = client.get(f"{API}/admin/metrics/priorities", headers=ha()).json()["data"]
    assert set(p) == {"reviews_pending", "destinations_out_of_engine", "announcements_expiring_7d"}
    assert all(isinstance(v, int) and v >= 0 for v in p.values())
    tok = create_access_token(data={"sub": "nadie", "role": "traveler"})
    assert client.get(f"{API}/admin/metrics/activity", headers={"Authorization": f"Bearer {tok}"}).status_code in (401, 403)


def test_detalle_sin_mes_usa_el_mes_actual(client):
    ctx = client.get(f"{API}/destinations/{DEST}").json()["data"]["context"]
    assert ctx["weather_category"] is not None and ctx["crowd_level"] is not None
