"""
Contexto mensual (tesis, Fase 4): filtros de clima/afluencia, calendario de 12 meses y nivel de costo.
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
from app.services.destination_context_service import climate_level
from app.services.recommendation_engine_v1 import generate_recommendations
from app.utils.hash_util import get_password_hash

API = "/api/v1"
DEST = "machu_picchu"
ADMIN = "ZCTX_ADMIN"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def seeded_and_admin():
    db = SessionLocal()
    if db.query(Destination).filter_by(destination_id=DEST).first() is None:
        db.close()
        pytest.skip("BD sin datos: ejecuta scripts/seed_from_thesis.py")
    original = db.query(TourismCatalog).filter_by(destination_id=DEST).first().cost_level
    db.query(User).filter_by(user_id=ADMIN).delete()
    db.add(User(user_id=ADMIN, name="Ctx Admin", email="zctx.admin@mailinator.com",
                password_hash=get_password_hash("ClaveSegura123"), role="admin", is_active=True, account_status="active"))
    db.commit()
    yield
    db.expire_all()  # la API cambió datos en otras sesiones: releer antes de restaurar
    cat = db.query(TourismCatalog).filter_by(destination_id=DEST).first()
    if cat:
        cat.cost_level = original  # restaura el valor que tenía antes de la prueba
    db.query(User).filter_by(user_id=ADMIN).delete()
    db.commit()
    db.close()


def test_umbrales_de_la_tesis():
    assert climate_level(0.70) == "Favorable"
    assert climate_level(0.699) == "Moderado"
    assert climate_level(0.50) == "Moderado"
    assert climate_level(0.49) == "Desfavorable"
    assert climate_level(None) is None


def test_contexto_del_mes_cubre_los_destinos(client):
    r = client.get(f"{API}/destinations/month-context", params={"month": 7})
    assert r.status_code == 200
    items = r.json()["data"]
    assert len(items) >= 14
    first = items[0]
    for key in ("destination_id", "clima_por_preferencia", "clima_nivel", "clima_riesgo", "aforo_nivel", "visitantes_medios"):
        assert key in first
    assert set(first["clima_por_preferencia"]) == {"frio", "templado", "calido", "seco", "indiferente"}
    assert first["aforo_nivel"] in ("Bajo", "Medio", "Alto")


def test_contexto_del_mes_valida_el_mes(client):
    assert client.get(f"{API}/destinations/month-context", params={"month": 13}).status_code == 422
    assert client.get(f"{API}/destinations/month-context").status_code == 422


def test_calendario_trae_12_meses_con_la_explicacion_de_la_tesis(client):
    r = client.get(f"{API}/destinations/{DEST}/calendar", params={"clima": "cálido", "tolerancia": "media"})
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["preference"] == "calido" and d["tolerance"] == "media"
    assert [m["month"] for m in d["months"]] == list(range(1, 13))
    julio = d["months"][6]
    assert julio["clima_nivel"] in ("Favorable", "Moderado", "Desfavorable")
    assert "julio" in julio["clima_explicacion"].lower()
    assert "visitantes" in julio["aforo_explicacion"].lower()
    assert julio["visitantes_medios"] > 0
    assert d["best_month"] != d["worst_month"]


def test_calendario_sin_parametros_usa_valores_neutros(client):
    d = client.get(f"{API}/destinations/{DEST}/calendar").json()["data"]
    assert d["preference"] == "indiferente" and d["tolerance"] == "media"


def test_calendario_destino_inexistente(client):
    assert client.get(f"{API}/destinations/no_existe/calendar").status_code == 404


@pytest.mark.parametrize("clima,tol", [("calido", "media"), ("frio", "baja"), ("seco", "alta"), ("templado", "media")])
def test_el_mejor_mes_del_calendario_coincide_con_el_del_motor(client, clima, tol):
    """El calendario y las recomendaciones deben hablar del mismo «mejor mes»."""
    cal = client.get(f"{API}/destinations/{DEST}/calendar", params={"clima": clima, "tolerancia": tol}).json()["data"]
    perfil = {"perfil_turistico": "cultural", "intereses": ["cultura", "historia"], "clima_preferido": clima, "tolerancia_multitudes": tol}
    recs = generate_recommendations(perfil, limit=14, month=7)
    mine = next(r for r in recs if r["destination_id"] == DEST)
    assert mine["best_month"] == cal["best_month"]


def test_nivel_de_costo_se_edita_desde_el_panel_y_sale_en_la_lista(client):
    h = {"Authorization": f"Bearer {create_access_token({'sub': ADMIN})}"}
    assert client.patch(f"{API}/admin/destinations/{DEST}", headers=h, json={"cost_level": "ALTO "}).status_code == 200
    item = next(d for d in client.get(f"{API}/destinations").json()["data"] if d["destination_id"] == DEST)
    assert item["cost_level"] == "alto"
    assert client.get(f"{API}/destinations/{DEST}").json()["data"]["cost_level"] == "alto"

    assert client.patch(f"{API}/admin/destinations/{DEST}", headers=h, json={"cost_level": "carísimo"}).status_code == 422
    # null lo borra
    assert client.patch(f"{API}/admin/destinations/{DEST}", headers=h, json={"cost_level": None}).status_code == 200
    assert client.get(f"{API}/destinations/{DEST}").json()["data"]["cost_level"] is None


def test_nivel_de_costo_requiere_ser_admin(client):
    assert client.patch(f"{API}/admin/destinations/{DEST}", json={"cost_level": "bajo"}).status_code == 401
