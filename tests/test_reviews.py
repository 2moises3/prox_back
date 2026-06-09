"""
PROXVEL Backend - Tests de Reviews y Users.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_get_demo_users(client):
    response = client.get("/api/v1/users/demo")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # At least we expect a list
    assert isinstance(data["data"], list)

def test_create_review_invalid_user(client):
    payload = {
        "user_id": "U99999", # Invalid user
        "destination_id": "machu-picchu",
        "rating_general": 5,
        "review_text": "Excelente",
        "aspect_ratings": []
    }
    response = client.post("/api/v1/reviews", json=payload)
    assert response.status_code == 404
    assert "Usuario no existe" in response.json()["detail"]

def test_create_review_invalid_destination(client):
    payload = {
        "user_id": "U00001",
        "destination_id": "invalid-dest", # Invalid destination
        "rating_general": 5,
        "review_text": "Excelente",
        "aspect_ratings": []
    }
    response = client.post("/api/v1/reviews", json=payload)
    assert response.status_code == 404
    assert "Destino no existe" in response.json()["detail"]

def test_create_review_success(client):
    payload = {
        "user_id": "U00001",
        "destination_id": "machu-picchu",
        "rating_general": 4,
        "review_text": "Muy bonito lugar.",
        "aspect_ratings": [
            {"aspect": "atractivos", "rating": 5, "comment": "Genial"},
            {"aspect": "costos", "rating": 3, "comment": "Caro"}
        ]
    }
    response = client.post("/api/v1/reviews", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["review_id"] is not None
    assert data["data"]["status"] == "pending_processing"
    assert len(data["data"]["aspect_ratings"]) == 2

def test_get_reviews_by_destination(client):
    response = client.get("/api/v1/reviews/destination/machu-picchu")
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_get_reviews_by_user(client):
    response = client.get("/api/v1/reviews/user/U00001")
    assert response.status_code == 200
    assert response.json()["success"] is True

def test_get_pending_reviews(client):
    response = client.get("/api/v1/reviews/pending")
    assert response.status_code == 200
    assert response.json()["success"] is True
