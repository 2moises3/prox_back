"""
Anuncios internos: validación de la acción del botón, fechas en UTC, anuncios por destino y métricas.
Necesita los datos de `python scripts/seed_from_thesis.py`; si la BD está vacía se omite.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config.database import SessionLocal
from app.core.rate_limit import announcement_events
from app.core.security import create_access_token
from app.models.announcement_model import Announcement
from app.models.destination_model import Destination
from app.models.user_model import User
from app.utils.hash_util import get_password_hash

API = "/api/v1"
ADMIN = "ZANN_ADMIN"
TITLE = "ZANN prueba"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def admin():
    db = SessionLocal()
    if db.query(Destination).filter_by(destination_id="chan_chan").first() is None:
        db.close()
        pytest.skip("BD sin datos: ejecuta scripts/seed_from_thesis.py")
    db.query(User).filter_by(user_id=ADMIN).delete()
    db.add(User(user_id=ADMIN, name="Ann Admin", email="zann.admin@mailinator.com",
                password_hash=get_password_hash("ClaveSegura123"), role="admin",
                is_active=True, account_status="active"))
    db.commit()
    yield
    db.query(Announcement).filter(Announcement.title.like("ZANN%")).delete(synchronize_session=False)
    db.query(User).filter_by(user_id=ADMIN).delete()
    db.commit()
    db.close()


@pytest.fixture
def h():
    return {"Authorization": f"Bearer {create_access_token(data={'sub': ADMIN, 'role': 'admin'})}"}


def _create(client, h, **extra):
    body = {"title": TITLE, "message": "Mensaje", "placement": "home_top", **extra}
    return client.post(f"{API}/admin/announcements", json=body, headers=h)


@pytest.mark.parametrize("url", ["/destination/machu_picchu", "/search", "/profile/preferences", "https://tuboleto.cultura.pe"])
def test_acciones_validas(client, h, url):
    r = _create(client, h, cta_text="Ver", cta_url=url)
    assert r.status_code == 201, r.text
    assert r.json()["data"]["cta_url"] == url


@pytest.mark.parametrize("url", ["javascript:alert(1)", "http://inseguro.com", "/admin", "/destination/../x"])
def test_acciones_invalidas(client, h, url):
    assert _create(client, h, cta_text="Ver", cta_url=url).status_code == 422


def test_boton_exige_texto_y_accion(client, h):
    assert _create(client, h, cta_text="Ver").status_code == 422
    assert _create(client, h, cta_url="/search").status_code == 422


def test_destino_del_boton_debe_existir(client, h):
    assert _create(client, h, cta_text="Ver", cta_url="/destination/no_existe").status_code == 422


def test_fechas_en_utc_con_z(client, h):
    # 10:00 en Lima (UTC-5) = 15:00 UTC; se guarda y devuelve en UTC con 'Z'.
    r = _create(client, h, starts_at="2030-01-01T10:00:00-05:00", ends_at="2030-01-02T10:00:00-05:00")
    data = r.json()["data"]
    assert data["starts_at"] == "2030-01-01T15:00:00Z"
    assert data["status"] == "scheduled"


def test_anuncio_por_destino(client, h):
    r = _create(client, h, placement="destination_detail", target_destination_id="chan_chan")
    ann_id = r.json()["data"]["id"]
    assert r.json()["data"]["target_destination_name"]

    general = _create(client, h, placement="destination_detail").json()["data"]["id"]

    def ids(dest):
        res = client.get(f"{API}/announcements/active", params={"placement": "destination_detail", "destination_id": dest})
        return {a["id"] for a in res.json()["data"]}

    assert {ann_id, general} <= ids("chan_chan")
    assert ann_id not in ids("machu_picchu") and general in ids("machu_picchu")


def test_destino_objetivo_se_limpia_fuera_del_detalle(client, h):
    r = _create(client, h, placement="home_top", target_destination_id="chan_chan")
    assert r.json()["data"]["target_destination_id"] is None


def test_metricas(client, h):
    announcement_events.reset()
    ann_id = _create(client, h).json()["data"]["id"]
    for ev in ("impression", "impression", "click", "dismiss"):
        assert client.post(f"{API}/announcements/{ann_id}/events", json={"event": ev}).status_code == 200
    data = client.get(f"{API}/admin/announcements/{ann_id}", headers=h).json()["data"]
    assert (data["impressions"], data["clicks"], data["dismissals"]) == (2, 1, 1)
    assert client.post(f"{API}/announcements/{ann_id}/events", json={"event": "otro"}).status_code == 422
    assert client.post(f"{API}/announcements/999999/events", json={"event": "click"}).status_code == 404


def test_metricas_con_limite(client, h):
    announcement_events.reset()
    ann_id = _create(client, h).json()["data"]["id"]
    codes = [client.post(f"{API}/announcements/{ann_id}/events", json={"event": "impression"}).status_code
             for _ in range(125)]
    assert codes.count(429) >= 1
    announcement_events.reset()


def test_publico_no_expone_metricas(client, h):
    _create(client, h)
    items = client.get(f"{API}/announcements/active").json()["data"]
    assert items and all("impressions" not in a and "created_by" not in a for a in items)


def test_expirado_no_se_publica(client, h):
    past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    ended = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    ann_id = _create(client, h, starts_at=past, ends_at=ended).json()["data"]["id"]
    items = client.get(f"{API}/announcements/active").json()["data"]
    assert ann_id not in {a["id"] for a in items}
