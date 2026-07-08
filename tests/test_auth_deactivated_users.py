import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config.database import SessionLocal
from app.models.user_model import User
from app.utils.hash_util import get_password_hash
from app.repositories import db_user_repository

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

DUMMY_EMAIL = "test.deactivated@proxvel.com"
DUMMY_PASSWORD = "testpassword123"

@pytest.fixture(scope="module")
def setup_dummy_user():
    # Crear usuario dummy
    db = SessionLocal()
    
    # Limpiar si ya existe
    existing = db_user_repository.get_user_by_email(DUMMY_EMAIL)
    if existing:
        db_user_repository.delete_user_record(db, existing.user_id)
        db.commit()
        
    user_id = db_user_repository.get_next_user_id()
    hashed = get_password_hash(DUMMY_PASSWORD)
    
    new_user = User(
        user_id=user_id,
        name="Test Deactivated",
        email=DUMMY_EMAIL,
        password_hash=hashed,
        role="traveler",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()
    
    yield new_user.user_id
    
    # Teardown
    db = SessionLocal()
    db_user_repository.delete_user_record(db, user_id)
    db.commit()
    db.close()

def test_login_active_user(client, setup_dummy_user):
    # Usuario activo debe poder hacer login
    response = client.post("/api/v1/auth/login", json={
        "email": DUMMY_EMAIL,
        "password": DUMMY_PASSWORD
    })
    assert response.status_code == 200
    assert "access_token" in response.json()["data"]

def test_login_deactivated_user(client, setup_dummy_user):
    user_id = setup_dummy_user
    
    # Desactivar usuario
    db_user_repository.update_user(user_id, {"is_active": False})
    
    # Intentar login
    response = client.post("/api/v1/auth/login", json={
        "email": DUMMY_EMAIL,
        "password": DUMMY_PASSWORD
    })
    
    # Ya NO debería devolver 200, sino 403
    assert response.status_code == 403
    assert "Cuenta desactivada" in response.json()["detail"]
    assert "data" not in response.json() or "access_token" not in response.json().get("data", {})

def test_access_protected_route_with_old_token(client, setup_dummy_user):
    user_id = setup_dummy_user
    
    # Activar usuario primero para obtener token
    db_user_repository.update_user(user_id, {"is_active": True})
    
    response = client.post("/api/v1/auth/login", json={
        "email": DUMMY_EMAIL,
        "password": DUMMY_PASSWORD
    })
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    
    # Probar que el token funciona
    headers = {"Authorization": f"Bearer {token}"}
    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    
    # Desactivar usuario
    db_user_repository.update_user(user_id, {"is_active": False})
    
    # Usar el token viejo, debe fallar pasivamente en get_current_user
    blocked_response = client.get("/api/v1/auth/me", headers=headers)
    assert blocked_response.status_code == 403
    assert "Cuenta desactivada" in blocked_response.json()["detail"]

def test_deactivated_user_blocks_registration(client, setup_dummy_user):
    user_id = setup_dummy_user
    db_user_repository.update_user(user_id, {"is_active": False})
    
    # Intentar registrar mismo email
    response = client.post("/api/v1/users", json={
        "name": "Another Guy",
        "email": DUMMY_EMAIL,
        "password": "anotherpassword123"
    })
    
    # Debe ser 409 Conflict
    assert response.status_code == 409
    assert "ya está registrado" in response.json()["detail"]

def test_full_delete_frees_email(client, setup_dummy_user):
    user_id = setup_dummy_user
    
    # Borrar usuario full (Hard Delete)
    db = SessionLocal()
    db_user_repository.delete_user_record(db, user_id)
    db.commit()
    db.close()
    
    # Registrar de nuevo
    response = client.post("/api/v1/users", json={
        "name": "New Guy",
        "email": DUMMY_EMAIL,
        "password": "newpassword123"
    })
    
    # Debe ser 201 Created (el correo se liberó)
    assert response.status_code == 201
    
    # Teardown del nuevo
    new_id = response.json()["data"]["user_id"]
    db = SessionLocal()
    db_user_repository.delete_user_record(db, new_id)
    db.commit()
    db.close()
