"""
PROXVEL Backend - Tests de Health, Data Status y Tourism Catalog.
Smoke tests básicos para verificar que los endpoints responden correctamente.
Incluye tests de Fase 1B (catálogo turístico).
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    """TestClient que ejecuta el lifespan completo (carga CSV al inicio)."""
    with TestClient(app) as c:
        yield c


# ── Tests Fase 1 (existentes) ──────────────────────────────────────

def test_health_returns_200(client):
    """El endpoint /health debe responder con status 200 y datos correctos."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "PROXVEL Backend"
    assert "version" in data


def test_data_status_returns_200(client):
    """El endpoint /data/status debe responder con el modo de datos y estado."""
    response = client.get("/api/v1/data/status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    payload = data["data"]
    assert "data_mode" in payload
    assert "csv_status" in payload
    assert "database_status" in payload
    assert "fallback_available" in payload


def test_destinations_returns_200(client):
    """El endpoint /destinations debe responder con lista de destinos."""
    response = client.get("/api/v1/destinations")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_contextual_ranking_returns_200(client):
    """El endpoint /recommendations/contextual debe responder correctamente."""
    response = client.get("/api/v1/recommendations/contextual")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_search_returns_200(client):
    """El endpoint /recommendations/search debe responder correctamente."""
    response = client.get("/api/v1/recommendations/search?query=Machu")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_base_recommendations_returns_200(client):
    """El endpoint /recommendations/base debe responder con stub."""
    response = client.get("/api/v1/recommendations/base")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_destination_detail_not_found(client):
    """Debe devolver 404 para un destino que no existe."""
    response = client.get("/api/v1/destinations/destino-inexistente")
    assert response.status_code == 404


def test_destination_detail_machu_picchu(client):
    """Debe devolver detalle de Machu Picchu con tourism_info."""
    response = client.get("/api/v1/destinations/machu-picchu")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["destination"] == "Machu Picchu"
    # Fase 1B: debe incluir tourism_info
    assert "tourism_info" in data["data"]


# ── Tests Fase 1B (catálogo turístico) ────────────────────────────

def test_tourism_catalog_returns_200(client):
    """El endpoint /tourism/catalog debe devolver los 3 destinos."""
    response = client.get("/api/v1/tourism/catalog")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert data["count"] == 3


def test_tourism_catalog_detail_returns_200(client):
    """El endpoint /tourism/catalog/{id} debe devolver detalle turístico."""
    response = client.get("/api/v1/tourism/catalog/machu-picchu")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["destination"] == "Machu Picchu"
    assert data["data"]["official_source_name"] is not None
    assert isinstance(data["data"]["gallery_images"], list)


def test_tourism_catalog_detail_not_found(client):
    """Debe devolver 404 para un destino no existente en catálogo."""
    response = client.get("/api/v1/tourism/catalog/destino-inexistente")
    assert response.status_code == 404


def test_tourism_map_markers_returns_200(client):
    """El endpoint /tourism/map-markers debe responder sin errores."""
    response = client.get("/api/v1/tourism/map-markers")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    # Las coordenadas ya no están PENDIENTE, así que debe retornar 3 MVP
    assert data["count"] == 3


def test_destinations_enriched_with_catalog(client):
    """Los destinos deben incluir city y category del catálogo."""
    response = client.get("/api/v1/destinations")
    assert response.status_code == 200
    data = response.json()
    # Buscar Machu Picchu
    machu = next(
        (d for d in data["data"] if d["destination_id"] == "machu-picchu"),
        None,
    )
    assert machu is not None
    assert machu["city"] == "Machupicchu"
    assert machu["region"] == "Cusco"
    assert machu["category"] == "Manifestaciones Culturales"


def test_contextual_ranking_enriched(client):
    """El ranking contextual debe incluir datos del catálogo."""
    response = client.get("/api/v1/recommendations/contextual?user_id=U00001")
    assert response.status_code == 200
    data = response.json()
    if data["data"]:
        first = data["data"][0]
        # Debe tener campos enriquecidos
        assert "city" in first
        assert "tourism_summary" in first
        # Scores no deben haber cambiado
        assert "compatibility_percentage" in first
        assert "final_score" in first
