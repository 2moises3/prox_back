"""
PROXVEL Backend - Tests de Reviews.

Usa un viajero y un admin temporales (prefijo ZREV) y borra las reseñas que crea.
Las reseñas necesitan un destino real: `python scripts/seed_from_thesis.py`.
"""
import pytest
import os
from fastapi.testclient import TestClient

from app.main import app
from app.config.database import SessionLocal
from app.core.security import create_access_token
from app.models.destination_model import Destination
from app.models.review_model import Review
from app.models.review_aspect_rating_model import ReviewAspectRating
from app.models.review_report_model import ReviewReport
from app.models.user_model import User
from app.utils.hash_util import get_password_hash

TRAVELER_ID, OTHER_ID, ADMIN_ID = "ZREV_T", "ZREV_O", "ZREV_A"
DEST_ID = "machu_picchu"
API = "/api/v1"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def headers_for(user_id: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(data={'sub': user_id})}"}


@pytest.fixture(scope="module", autouse=True)
def temp_users():
    db = SessionLocal()
    created_destination = False
    if os.getenv("PROXVEL_ISOLATED_REVIEWS_TEST") == "1":
        assert db.bind.url.database.startswith("proxvel_review_test_")
        assert db.query(Destination).filter_by(destination_id=DEST_ID).first() is None
        db.add(Destination(destination_id=DEST_ID, destination="Machu Picchu (fixture)",
                           in_engine=False))
        db.commit()
        created_destination = True
    ids = [TRAVELER_ID, OTHER_ID, ADMIN_ID]

    def purge():
        review_ids = [r.review_id for r in db.query(Review).filter(Review.user_id.in_(ids)).all()]
        if review_ids:
            db.query(ReviewReport).filter(ReviewReport.review_id.in_(review_ids)).delete(synchronize_session=False)
            db.query(ReviewAspectRating).filter(ReviewAspectRating.review_id.in_(review_ids)).delete(synchronize_session=False)
            db.query(Review).filter(Review.review_id.in_(review_ids)).delete(synchronize_session=False)
        db.query(User).filter(User.user_id.in_(ids)).delete(synchronize_session=False)
        db.commit()

    purge()
    for uid, role in ((TRAVELER_ID, "traveler"), (OTHER_ID, "traveler"), (ADMIN_ID, "admin")):
        db.add(User(user_id=uid, name=uid, email=f"{uid.lower()}@mailinator.com",
                    password_hash=get_password_hash("ClaveSegura123"), role=role,
                    is_active=True, account_status="active"))
    db.commit()
    has_dest = db.query(Destination).filter_by(destination_id=DEST_ID).first() is not None
    yield has_dest
    purge()
    if created_destination:
        db.query(Destination).filter_by(destination_id=DEST_ID).delete()
        db.commit()
    db.close()


@pytest.fixture
def need_dest(temp_users):
    if not temp_users:
        pytest.skip("BD sin datos: ejecuta scripts/seed_from_thesis.py")


def review_payload(**over):
    base = {
        "user_id": TRAVELER_ID,
        "destination_id": DEST_ID,
        "rating_general": 4,
        "review_text": "Muy bonito lugar.",
        "aspect_ratings": [
            {"aspect": "atractivos", "rating": 5, "comment": "Genial"},
            {"aspect": "costos", "rating": 3, "comment": "Caro"},
        ],
    }
    return {**base, **over}


def test_users_demo_no_es_publico(client):
    assert client.get(f"{API}/users/demo").status_code == 401


def test_create_review_invalid_user(client):
    # El usuario U99999 no existe en la BD: el token se rechaza con 401.
    response = client.post(f"{API}/reviews", json=review_payload(user_id="U99999"), headers=headers_for("U99999"))
    assert response.status_code == 401
    assert "Credenciales inválidas" in response.json()["detail"]


def test_create_review_invalid_destination(client):
    response = client.post(f"{API}/reviews", json=review_payload(destination_id="invalid-dest"),
                           headers=headers_for(TRAVELER_ID))
    assert response.status_code == 404
    assert "Destino no existe" in response.json()["detail"]


def test_create_review_requires_login(client):
    assert client.post(f"{API}/reviews", json=review_payload()).status_code == 401


def test_create_review_success(client, need_dest):
    response = client.post(f"{API}/reviews", json=review_payload(), headers=headers_for(TRAVELER_ID))
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["review_id"] is not None
    assert data["data"]["status"] == "pending_processing"
    assert len(data["data"]["aspect_ratings"]) == 2


def test_create_review_ignores_spoofed_user_id(client, need_dest):
    """El user_id del cuerpo se ignora: la reseña es del usuario autenticado."""
    response = client.post(f"{API}/reviews", json=review_payload(user_id=OTHER_ID), headers=headers_for(TRAVELER_ID))
    assert response.status_code == 201
    assert response.json()["data"]["user_id"] == TRAVELER_ID


def test_get_reviews_by_destination_requires_login(client):
    assert client.get(f"{API}/reviews/destination/{DEST_ID}").status_code == 401


def test_get_reviews_by_destination(client):
    response = client.get(f"{API}/reviews/destination/{DEST_ID}", headers=headers_for(TRAVELER_ID))
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_get_reviews_by_user(client):
    response = client.get(f"{API}/reviews/user/{TRAVELER_ID}", headers=headers_for(TRAVELER_ID))
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_cannot_read_reviews_of_another_user(client):
    response = client.get(f"{API}/reviews/user/{TRAVELER_ID}", headers=headers_for(OTHER_ID))
    assert response.status_code == 403


def test_get_pending_reviews_only_for_admin(client):
    assert client.get(f"{API}/reviews/pending").status_code == 401
    assert client.get(f"{API}/reviews/pending", headers=headers_for(TRAVELER_ID)).status_code == 403
    response = client.get(f"{API}/reviews/pending", headers=headers_for(ADMIN_ID))
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_review_by_id_only_owner_or_admin(client, need_dest):
    created = client.post(f"{API}/reviews", json=review_payload(), headers=headers_for(TRAVELER_ID)).json()["data"]
    rid = created["review_id"]
    assert client.get(f"{API}/reviews/{rid}", headers=headers_for(TRAVELER_ID)).status_code == 200
    assert client.get(f"{API}/reviews/{rid}", headers=headers_for(ADMIN_ID)).status_code == 200
    assert client.get(f"{API}/reviews/{rid}", headers=headers_for(OTHER_ID)).status_code == 403
    assert client.get(f"{API}/reviews/{rid}").status_code == 401

def test_public_visibility_ownership_and_dates(client, need_dest):
    created = client.post(f"{API}/reviews", json=review_payload(), headers=headers_for(TRAVELER_ID)).json()["data"]
    rid = created["review_id"]
    assert created["created_at"]
    own = client.get(f"{API}/reviews/destination/{DEST_ID}", headers=headers_for(TRAVELER_ID)).json()["data"]
    row = next(r for r in own if r["review_id"] == rid)
    assert row["is_own"] is True
    assert "user_id" not in row and "status" not in row
    assert row["created_at"] and row["is_hidden"] is False
    others = client.get(f"{API}/reviews/destination/{DEST_ID}", headers=headers_for(OTHER_ID)).json()["data"]
    assert next(r for r in others if r["review_id"] == rid)["is_own"] is False
    assert client.patch(f"{API}/reviews/{rid}/hidden", json={"hidden": True}, headers=headers_for(TRAVELER_ID)).status_code == 403
    assert client.patch(f"{API}/reviews/{rid}/hidden", json={"hidden": True}, headers=headers_for(ADMIN_ID)).status_code == 200
    visible = client.get(f"{API}/reviews/destination/{DEST_ID}", headers=headers_for(OTHER_ID)).json()["data"]
    assert all(r["review_id"] != rid for r in visible)
    mine = client.get(f"{API}/reviews/user/{TRAVELER_ID}", headers=headers_for(TRAVELER_ID)).json()["data"]
    row = next(r for r in mine if r["review_id"] == rid)
    assert row["is_hidden"] is True
    assert row["destination_name"] and row["created_at"]


def test_report_confirmation_is_idempotent(client, need_dest):
    rid = client.post(f"{API}/reviews", json=review_payload(), headers=headers_for(TRAVELER_ID)).json()["data"]["review_id"]
    route = f"{API}/reviews/{rid}/report"
    assert client.post(route, json={"reason": "spam"}, headers=headers_for(TRAVELER_ID)).status_code == 409
    assert client.post(route, json={"reason": "invalid"}, headers=headers_for(OTHER_ID)).status_code == 422
    for _ in range(2):
        assert client.post(route, json={"reason": "spam"}, headers=headers_for(OTHER_ID)).status_code == 200
    with SessionLocal() as db:
        assert db.query(ReviewReport).filter_by(review_id=rid, reporter_user_id=OTHER_ID).count() == 1


def test_empty_review_text_rejected(client, need_dest):
    response = client.post(f"{API}/reviews", json=review_payload(review_text="   "), headers=headers_for(TRAVELER_ID))
    assert response.status_code == 422
