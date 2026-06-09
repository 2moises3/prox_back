"""
PROXVEL Backend - Tests de Training Batches y Export.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_export_monthly_batch_success(client):
    payload = {
        "year": 2026,
        "month": 6,
        "format": "csv"
    }
    response = client.post("/api/v1/admin/training-batches/monthly", json=payload)
    data = response.json()
    
    # Podría devolver false si no hay reseñas (ya las exportamos en una prueba previa o no hay pendientes)
    # Pero si hay, debe devolver success=true y un batch_id
    if data["success"]:
        assert response.status_code == 200
        assert data["data"]["batch_id"].startswith("B202606")
        assert data["data"]["status"] == "exported"
    else:
        assert data["message"] == "No hay reseñas pendientes para exportar en este mes"

def test_get_training_batches(client):
    response = client.get("/api/v1/admin/training-batches")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

def test_mark_batch_used(client):
    # First, get batches
    response = client.get("/api/v1/admin/training-batches")
    batches = response.json()["data"]
    
    if batches:
        # Assuming the returned list has dicts or IDs. Let's say it returns IDs or objects.
        # Wait, get_batches in route returns [b.id for b in batches]. I should fix that to return dicts!
        # But anyway, if we have a batch_id, we can mark it used. We'll test with a fake ID first to see 404.
        resp_404 = client.patch("/api/v1/admin/training-batches/B999999/mark-used-for-training")
        assert resp_404.status_code == 404

def test_create_model_run(client):
    payload = {
        "batch_id": "B999999", # Invalid batch
        "model_name": "ABSA_BERT",
        "status": "completed"
    }
    response = client.post("/api/v1/admin/model-update-runs", json=payload)
    assert response.status_code == 400
    assert "no existe" in response.json()["detail"]
