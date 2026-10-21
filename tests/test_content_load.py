"""
Carga de la ficha comercial desde seed_data/destination_content.json (botón de Configuración en el dashboard).
Necesita los datos de `python scripts/seed_from_thesis.py`; si la BD está vacía se omite.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config.database import SessionLocal
from app.core.security import create_access_token
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.user_model import User
from app.services import content_seed_service
from app.utils.hash_util import get_password_hash

API = "/api/v1"
DEST = "machu_picchu"
ADMIN = "ZCNT_ADMIN"
SUPER = "ZCNT_SUPER"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def usuarios():
    db = SessionLocal()
    if db.query(Destination).filter_by(destination_id=DEST).first() is None:
        db.close()
        pytest.skip("BD sin datos: ejecuta scripts/seed_from_thesis.py")
    original = {f: getattr(db.query(TourismCatalog).filter_by(destination_id=DEST).first(), f)
                for f in content_seed_service.CONTENT_FIELDS}
    for uid, role in ((ADMIN, "admin"), (SUPER, "super_admin")):
        db.query(User).filter_by(user_id=uid).delete()
        db.add(User(user_id=uid, name=uid, email=f"{uid.lower()}@mailinator.com",
                    password_hash=get_password_hash("ClaveSegura123"), role=role,
                    is_active=True, account_status="active"))
    db.commit()
    yield
    db.expire_all()  # la API cambió datos en otras sesiones: releer antes de restaurar
    cat = db.query(TourismCatalog).filter_by(destination_id=DEST).first()
    for f, v in original.items():
        setattr(cat, f, v)
    for uid in (ADMIN, SUPER):
        db.query(User).filter_by(user_id=uid).delete()
    db.commit()
    db.close()


def _auth(uid, role):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': uid, 'role': role})}"}


def _set(field, value):
    db = SessionLocal()
    try:
        setattr(db.query(TourismCatalog).filter_by(destination_id=DEST).first(), field, value)
        db.commit()
    finally:
        db.close()


def _get(field):
    db = SessionLocal()
    try:
        return getattr(db.query(TourismCatalog).filter_by(destination_id=DEST).first(), field)
    finally:
        db.close()


def test_requiere_admin(client):
    assert client.post(f"{API}/admin/destinations/content/load", json={}).status_code in (401, 403)


def test_rellena_solo_vacios_y_respeta_lo_editado(client):
    _set("how_to_get", None)
    _set("description", "Texto editado a mano")
    r = client.post(f"{API}/admin/destinations/content/load", json={}, headers=_auth(ADMIN, "admin"))
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["overwrite"] is False
    assert data["destinations_in_file"] == 14
    assert data["missing_in_database"] == []
    assert _get("how_to_get")                       # se llenó el vacío
    assert _get("description") == "Texto editado a mano"   # lo editado no se pisa


def test_sobrescribir_exige_super_admin(client):
    r = client.post(f"{API}/admin/destinations/content/load", json={"overwrite": True},
                    headers=_auth(ADMIN, "admin"))
    assert r.status_code == 403
    assert _get("description") == "Texto editado a mano"

    r = client.post(f"{API}/admin/destinations/content/load", json={"overwrite": True},
                    headers=_auth(SUPER, "super_admin"))
    assert r.status_code == 200
    assert _get("description") != "Texto editado a mano"


def test_archivo_es_valido():
    content = content_seed_service.load_content_file()
    assert len(content) == 14
    for did, v in content.items():
        assert v["category"] in {"Arqueología", "Naturaleza", "Museo", "Recreación"}, did
        assert v["difficulty"] in {"facil", "moderada", "exigente"}, did
        assert -19 < v["latitude"] < 0 and -82 < v["longitude"] < -68, did
