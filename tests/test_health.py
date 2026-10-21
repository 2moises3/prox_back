"""
PROXVEL Backend - Tests de Health, Data Status y Tourism Catalog.
Smoke tests básicos para verificar que los endpoints responden correctamente.

Las rutas administrativas (/data/status, /recommendations/contextual|search|base)
exigen un admin: se crea uno temporal (prefijo ZHLT) y se elimina al terminar.
Los tests que leen el catálogo necesitan los datos cargados con
`python scripts/seed_from_thesis.py`; si la BD está vacía se omiten.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config.database import SessionLocal
from app.core.security import create_access_token
from app.models.destination_model import Destination
from app.models.user_model import User
from app.utils.hash_util import get_password_hash

ADMIN_ID = "ZHLT_ADMIN"
DEST_ID = "machu_picchu"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def admin_headers():
    db = SessionLocal()
    db.query(User).filter_by(user_id=ADMIN_ID).delete()
    db.add(User(user_id=ADMIN_ID, name="Health Admin", email="zhlt.admin@mailinator.com",
                password_hash=get_password_hash("ClaveSegura123"), role="admin",
                is_active=True, account_status="active"))
    db.commit()
    yield {"Authorization": f"Bearer {create_access_token({'sub': ADMIN_ID})}"}
    db.query(User).filter_by(user_id=ADMIN_ID).delete()
    db.commit()
    db.close()


@pytest.fixture(scope="module")
def seeded():
    """Omite los tests que dependen del catálogo si la BD está vacía."""
    db = SessionLocal()
    try:
        has_data = db.query(Destination).filter_by(destination_id=DEST_ID).first() is not None
    finally:
        db.close()
    if not has_data:
        pytest.skip("BD sin datos: ejecuta scripts/seed_from_thesis.py")


# ── Fase 1 ────────────────────────────────────────────────────────────

def test_health_returns_200(client):
    """El endpoint /health debe responder con status 200 y datos correctos."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "PROXVEL Backend"
    assert "version" in data


def test_data_status_returns_200(client, admin_headers):
    """El endpoint /data/status (solo admin) responde con el modo de datos y estado."""
    response = client.get("/api/v1/data/status", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    payload = data["data"]
    assert "data_mode" in payload
    assert "database_status" in payload


def test_destinations_returns_200(client):
    """El endpoint /destinations debe responder con lista de destinos."""
    response = client.get("/api/v1/destinations")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_contextual_ranking_returns_200(client, admin_headers):
    """El endpoint /recommendations/contextual (solo admin) debe responder correctamente."""
    response = client.get("/api/v1/recommendations/contextual", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_search_returns_200(client, admin_headers):
    """El endpoint /recommendations/search (solo admin) debe responder correctamente."""
    response = client.get("/api/v1/recommendations/search?query=Machu", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_base_recommendations_returns_200(client, admin_headers):
    """El endpoint /recommendations/base (solo admin) debe responder con stub."""
    response = client.get("/api/v1/recommendations/base", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_destination_detail_not_found(client):
    """Debe devolver 404 para un destino que no existe."""
    response = client.get("/api/v1/destinations/destino-inexistente")
    assert response.status_code == 404


def test_destination_detail_machu_picchu(client, seeded):
    """Debe devolver detalle de Machu Picchu con tourism_info."""
    response = client.get(f"/api/v1/destinations/{DEST_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Machu Picchu" in data["data"]["destination"]
    assert "tourism_info" in data["data"]


# ── Fase 1B (catálogo turístico) ──────────────────────────────────

def test_tourism_catalog_returns_200(client, seeded):
    """El endpoint /tourism/catalog debe devolver los destinos activos."""
    response = client.get("/api/v1/tourism/catalog")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert data["count"] >= 1


def test_tourism_catalog_detail_returns_200(client, seeded):
    """El endpoint /tourism/catalog/{id} debe devolver detalle turístico."""
    response = client.get(f"/api/v1/tourism/catalog/{DEST_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Machu Picchu" in data["data"]["destination"]
    assert isinstance(data["data"]["gallery_images"], list)
    # La ficha ya no arrastra campos heredados de MINCETUR.
    for legacy in ("official_source_name", "hierarchy", "experience_type", "subtype"):
        assert legacy not in data["data"]
    assert "recommended_duration" in data["data"]
    assert isinstance(data["data"]["interest_tags"], list)


def test_tourism_catalog_detail_not_found(client):
    """Debe devolver 404 para un destino no existente en catálogo."""
    response = client.get("/api/v1/tourism/catalog/destino-inexistente")
    assert response.status_code == 404


def test_tourism_map_markers_returns_200(client, seeded):
    """El endpoint /tourism/map-markers debe responder sin errores."""
    response = client.get("/api/v1/tourism/map-markers")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert data["count"] >= 1


def test_destinations_enriched_with_catalog(client, seeded):
    """Los destinos deben incluir los campos del catálogo (región, ciudad, categoría)."""
    response = client.get("/api/v1/destinations")
    assert response.status_code == 200
    data = response.json()
    machu = next((d for d in data["data"] if d["destination_id"] == DEST_ID), None)
    assert machu is not None
    for field in ("city", "region", "category", "in_engine"):
        assert field in machu
    assert "cusco" in (machu["region"] or "").lower()


def test_contextual_ranking_enriched(client, admin_headers):
    """El ranking contextual (solo admin) debe incluir datos del catálogo si hay filas."""
    response = client.get("/api/v1/recommendations/contextual?user_id=U00001", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    if data["data"]:
        first = data["data"][0]
        assert "city" in first
        assert "tourism_summary" in first
        assert "compatibility_percentage" in first
        assert "final_score" in first
