import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config.database import SessionLocal
from app.models.user_model import User
from app.repositories import db_user_repository
import hashlib
import os

client = TestClient(app)

DUMMY_EMAIL = "legacy_test@proxvel.com"
DUMMY_PASSWORD = "mysecretpassword"

def create_legacy_hash(password: str) -> str:
    iterations = 100000
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${key.hex()}"

@pytest.fixture(scope="function")
def legacy_user():
    db = SessionLocal()
    existing = db_user_repository.get_user_by_email(DUMMY_EMAIL)
    if existing:
        db_user_repository.delete_user_record(db, existing.user_id)
        db.commit()

    legacy_hash = create_legacy_hash(DUMMY_PASSWORD)
    user_id = db_user_repository.get_next_user_id()
    new_user = User(
        user_id=user_id,
        name="Legacy User",
        email=DUMMY_EMAIL,
        password_hash=legacy_hash,
        role="traveler",
        is_active=True,
        account_status="active"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()
    
    yield new_user.user_id
    
    db = SessionLocal()
    db_user_repository.delete_user_record(db, user_id)
    db.commit()
    db.close()

def test_login_legacy_works_and_rehashes(legacy_user):
    # Verificar que el hash actual es legacy
    db = SessionLocal()
    user = db_user_repository.get_user_by_id(legacy_user)
    assert user.password_hash.startswith("pbkdf2_sha256$")
    db.close()

    # Login
    response = client.post("/api/v1/auth/login", json={"email": DUMMY_EMAIL, "password": DUMMY_PASSWORD})
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]

    # Verificar rehash a bcrypt
    db = SessionLocal()
    user = db_user_repository.get_user_by_id(legacy_user)
    assert user.password_hash.startswith("$2b$")
    assert not user.password_hash.startswith("pbkdf2_sha256$")
    db.close()

def test_login_bcrypt_works(legacy_user):
    # Primero hacemos login para convertirlo a bcrypt
    client.post("/api/v1/auth/login", json={"email": DUMMY_EMAIL, "password": DUMMY_PASSWORD})
    
    # Login nuevamente ya con bcrypt
    response = client.post("/api/v1/auth/login", json={"email": DUMMY_EMAIL, "password": DUMMY_PASSWORD})
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]

def test_login_wrong_password_no_rehash(legacy_user):
    db = SessionLocal()
    user_before = db_user_repository.get_user_by_id(legacy_user)
    hash_before = user_before.password_hash
    db.close()

    response = client.post("/api/v1/auth/login", json={"email": DUMMY_EMAIL, "password": "wrongpassword"})
    assert response.status_code == 401

    db = SessionLocal()
    user_after = db_user_repository.get_user_by_id(legacy_user)
    assert user_after.password_hash == hash_before
    db.close()

def test_invalid_user_returns_401():
    response = client.post("/api/v1/auth/login", json={"email": "nonexistent@proxvel.com", "password": "password123"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Credenciales inválidas"

def test_inactive_user_no_rehash(legacy_user):
    # Marcar como inactivo
    db_user_repository.update_user(legacy_user, {"is_active": False})
    
    db = SessionLocal()
    user = db_user_repository.get_user_by_id(legacy_user)
    hash_before = user.password_hash
    db.close()

    response = client.post("/api/v1/auth/login", json={"email": DUMMY_EMAIL, "password": DUMMY_PASSWORD})
    assert response.status_code == 403

    db = SessionLocal()
    user_after = db_user_repository.get_user_by_id(legacy_user)
    assert user_after.password_hash == hash_before
    db.close()

def test_pending_deletion_no_login(legacy_user):
    db_user_repository.update_user(legacy_user, {"account_status": "pending_deletion"})

    response = client.post("/api/v1/auth/login", json={"email": DUMMY_EMAIL, "password": DUMMY_PASSWORD})
    assert response.status_code == 403

def test_deleted_user_no_login(legacy_user):
    db_user_repository.update_user(legacy_user, {"account_status": "deleted"})

    response = client.post("/api/v1/auth/login", json={"email": DUMMY_EMAIL, "password": DUMMY_PASSWORD})
    assert response.status_code == 403

def test_new_user_gets_bcrypt_on_create():
    # Asumiendo que el endpoint de creación de admin usa create_user_admin
    from app.services.user_admin_service import create_user_admin
    
    # Limpieza
    db = SessionLocal()
    existing = db_user_repository.get_user_by_email("new_bcrypt@proxvel.com")
    if existing:
        db_user_repository.delete_user_record(db, existing.user_id)
        db.commit()
    db.close()
    
    user, error, status = create_user_admin(
        name="New Bcrypt",
        email="new_bcrypt@proxvel.com",
        password="password123",
        role="admin"
    )
    assert user is not None
    assert error is None
    
    db = SessionLocal()
    db_user = db_user_repository.get_user_by_id(user.user_id)
    assert db_user.password_hash.startswith("$2b$")
    db_user_repository.delete_user_record(db, db_user.user_id)
    db.commit()
    db.close()
