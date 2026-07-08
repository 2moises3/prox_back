import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.config.database import SessionLocal
from app.models.user_model import User
from app.utils.hash_util import get_password_hash
from app.repositories import db_user_repository
from app.core.security import create_access_token

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# Usuarios de prueba
DUMMY_TRAVELER_EMAIL = "traveler.lifecycle@proxvel.com"
DUMMY_ADMIN_EMAIL = "admin.lifecycle@proxvel.com"
DUMMY_SUPERADMIN_EMAIL = "superadmin.lifecycle@proxvel.com"
DUMMY_PASSWORD = "testpassword123"

@pytest.fixture(scope="module")
def setup_users():
    db = SessionLocal()
    users_to_clean = [DUMMY_TRAVELER_EMAIL, DUMMY_ADMIN_EMAIL, DUMMY_SUPERADMIN_EMAIL]
    
    # Limpieza inicial
    for email in users_to_clean:
        existing = db_user_repository.get_user_by_email(email)
        if existing:
            db_user_repository.delete_user_record(db, existing.user_id)
            db.commit()

    hashed = get_password_hash(DUMMY_PASSWORD)
    
    # 1. Traveler
    t_id = db_user_repository.get_next_user_id()
    t_user = User(
        user_id=t_id,
        name="Traveler Lifecycle",
        email=DUMMY_TRAVELER_EMAIL,
        password_hash=hashed,
        role="traveler",
        is_active=True,
        account_status="active"
    )
    db.add(t_user)
    db.commit()
    db.refresh(t_user)

    # 2. Admin
    a_id = db_user_repository.get_next_user_id()
    a_user = User(
        user_id=a_id,
        name="Admin Lifecycle",
        email=DUMMY_ADMIN_EMAIL,
        password_hash=hashed,
        role="admin",
        is_active=True,
        account_status="active"
    )
    db.add(a_user)
    db.commit()
    db.refresh(a_user)

    # 3. Super Admin
    sa_id = db_user_repository.get_next_user_id()
    sa_user = User(
        user_id=sa_id,
        name="Super Admin Lifecycle",
        email=DUMMY_SUPERADMIN_EMAIL,
        password_hash=hashed,
        role="super_admin",
        is_active=True,
        account_status="active"
    )
    db.add(sa_user)
    db.commit()
    db.refresh(sa_user)
    
    db.close()

    yield {
        "traveler_id": t_id,
        "admin_id": a_id,
        "superadmin_id": sa_id
    }

    # Teardown
    db = SessionLocal()
    for email in users_to_clean:
        existing = db_user_repository.get_user_by_email(email)
        if existing:
            db_user_repository.delete_user_record(db, existing.user_id)
            db.commit()
    
    # También limpiar el de process deletions
    # Podría haber cambiado su email a @deleted.local
    deleted_guy = db.query(User).filter(User.name == "Usuario eliminado").all()
    for dg in deleted_guy:
        db_user_repository.delete_user_record(db, dg.user_id)
    db.commit()
    db.close()

def get_superadmin_token(client):
    response = client.post("/api/v1/auth/login", json={"email": DUMMY_SUPERADMIN_EMAIL, "password": DUMMY_PASSWORD})
    return response.json()["data"]["access_token"]

def get_admin_token(client):
    response = client.post("/api/v1/auth/login", json={"email": DUMMY_ADMIN_EMAIL, "password": DUMMY_PASSWORD})
    return response.json()["data"]["access_token"]

# 1. active puede login
def test_login_active_user(client, setup_users):
    # Restaurar a active
    db_user_repository.update_user(setup_users["traveler_id"], {"is_active": True, "account_status": "active"})
    response = client.post("/api/v1/auth/login", json={"email": DUMMY_TRAVELER_EMAIL, "password": DUMMY_PASSWORD})
    assert response.status_code == 200

# 2. disabled no puede login
def test_login_disabled_user(client, setup_users):
    db_user_repository.update_user(setup_users["traveler_id"], {"is_active": False, "account_status": "disabled"})
    response = client.post("/api/v1/auth/login", json={"email": DUMMY_TRAVELER_EMAIL, "password": DUMMY_PASSWORD})
    assert response.status_code == 403

# 3. pending_deletion no puede login
def test_login_pending_deletion_user(client, setup_users):
    db_user_repository.update_user(setup_users["traveler_id"], {"is_active": False, "account_status": "pending_deletion"})
    response = client.post("/api/v1/auth/login", json={"email": DUMMY_TRAVELER_EMAIL, "password": DUMMY_PASSWORD})
    assert response.status_code == 403

# 4. deleted no puede login
def test_login_deleted_user(client, setup_users):
    db_user_repository.update_user(setup_users["traveler_id"], {"is_active": False, "account_status": "deleted", "password_hash": "no_login"})
    response = client.post("/api/v1/auth/login", json={"email": DUMMY_TRAVELER_EMAIL, "password": DUMMY_PASSWORD})
    # Devuelve 401 Credenciales invalidas por el password_hash "no_login" o 403 por is_active
    assert response.status_code in [401, 403]

# 5. token viejo queda bloqueado para pending_deletion/deleted
def test_old_token_blocked(client, setup_users):
    # Activar y obtener token
    db_user_repository.update_user(setup_users["traveler_id"], {"is_active": True, "account_status": "active", "password_hash": get_password_hash(DUMMY_PASSWORD)})
    token = client.post("/api/v1/auth/login", json={"email": DUMMY_TRAVELER_EMAIL, "password": DUMMY_PASSWORD}).json()["data"]["access_token"]
    
    # Probar que funciona
    headers = {"Authorization": f"Bearer {token}"}
    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200

    # Pasar a pending_deletion
    db_user_repository.update_user(setup_users["traveler_id"], {"is_active": False, "account_status": "pending_deletion"})
    blocked_response = client.get("/api/v1/auth/me", headers=headers)
    assert blocked_response.status_code == 403

# 6. programar eliminación setea estado y fechas
def test_schedule_deletion(client, setup_users):
    db_user_repository.update_user(setup_users["traveler_id"], {"is_active": True, "account_status": "active"})
    token = get_superadmin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post(
        f"/api/v1/admin/users/{setup_users['traveler_id']}/schedule-deletion",
        json={"reason": "User requested"},
        headers=headers
    )
    assert response.status_code == 200
    
    user = db_user_repository.get_user_by_id(setup_users["traveler_id"])
    assert user.account_status == "pending_deletion"
    assert user.is_active is False
    assert user.deletion_requested_at is not None
    assert user.deletion_scheduled_at is not None
    assert user.deletion_reason == "User requested"
    assert user.deletion_requested_by == setup_users["superadmin_id"]

# 7. cancelar eliminación vuelve a disabled
def test_cancel_deletion(client, setup_users):
    token = get_superadmin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Intentar reactivar directamente
    status_response = client.patch(
        f"/api/v1/admin/users/{setup_users['traveler_id']}/status",
        json={"is_active": True},
        headers=headers
    )
    assert status_response.status_code == 409
    assert "Cancela la eliminación primero" in status_response.json()["detail"]

    # Cancelar la eliminación
    response = client.post(
        f"/api/v1/admin/users/{setup_users['traveler_id']}/cancel-deletion",
        headers=headers
    )
    assert response.status_code == 200
    
    user = db_user_repository.get_user_by_id(setup_users["traveler_id"])
    assert user.account_status == "disabled"
    assert user.is_active is False
    assert user.deletion_requested_at is None
    assert user.deletion_scheduled_at is None

    # Ahora sí, reactivar vía status
    status_response2 = client.patch(
        f"/api/v1/admin/users/{setup_users['traveler_id']}/status",
        json={"is_active": True},
        headers=headers
    )
    assert status_response2.status_code == 200
    user_reactivated = db_user_repository.get_user_by_id(setup_users["traveler_id"])
    assert user_reactivated.account_status == "active"
    assert user_reactivated.is_active is True

# 8. process-deletions anonimiza/ofusca y libera email original
# 9. email original puede registrarse de nuevo tras eliminación final
def test_process_deletions_and_reregister(client, setup_users):
    token = get_superadmin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Schedule deletion for the traveler
    client.post(
        f"/api/v1/admin/users/{setup_users['traveler_id']}/schedule-deletion",
        json={"reason": "Testing process_deletions"},
        headers=headers
    )
    
    # 2. Hack: Move deletion_scheduled_at to the past
    db = SessionLocal()
    u = db.query(User).filter(User.user_id == setup_users["traveler_id"]).first()
    u.deletion_scheduled_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
    db.commit()
    db.close()

    # 3. Process deletions
    response = client.post("/api/v1/admin/users/process-deletions", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["processed"] >= 1
    
    # 4. Verify user was obfuscated
    db = SessionLocal()
    u = db.query(User).filter(User.user_id == setup_users["traveler_id"]).first()
    assert u.account_status == "deleted"
    assert u.is_active is False
    assert u.name == "Usuario eliminado"
    assert "deleted.local" in u.email
    assert DUMMY_TRAVELER_EMAIL not in u.email
    db.close()
    
    # 5. Re-register original email
    register_response = client.post("/api/v1/users", json={
        "name": "New Traveler",
        "email": DUMMY_TRAVELER_EMAIL,
        "password": "newpassword123"
    })
    assert register_response.status_code == 201

# 10. admin no puede eliminarse a sí mismo
def test_admin_cannot_delete_self(client, setup_users):
    token = get_superadmin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post(
        f"/api/v1/admin/users/{setup_users['superadmin_id']}/schedule-deletion",
        json={"reason": "Self deletion"},
        headers=headers
    )
    assert response.status_code == 409
    assert "tu propia eliminación" in response.json()["detail"]

# 11. admin normal no puede eliminar super_admin
def test_admin_cannot_delete_superadmin(client, setup_users):
    token = get_admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.post(
        f"/api/v1/admin/users/{setup_users['superadmin_id']}/schedule-deletion",
        json={"reason": "Trying to delete boss"},
        headers=headers
    )
    assert response.status_code == 403

# 12. hard delete queda restringido a super_admin
def test_hard_delete_restricted(client, setup_users):
    # Admin normal intenta hard delete
    token = get_admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.delete(
        f"/api/v1/admin/users/{setup_users['traveler_id']}?mode=full",
        headers=headers
    )
    # Require super admin for DELETE /admin/users/{id}
    assert response.status_code == 403

    # Super admin sí puede
    sa_token = get_superadmin_token(client)
    sa_headers = {"Authorization": f"Bearer {sa_token}"}
    
    # Necesitamos alguien a quien borrar
    db = SessionLocal()
    new_id = db_user_repository.get_next_user_id()
    new_u = User(
        user_id=new_id,
        name="To Delete",
        email="todelete@test.com",
        password_hash=get_password_hash("password"),
        is_active=True,
        account_status="active"
    )
    db.add(new_u)
    db.commit()
    db.close()
    
    response2 = client.delete(f"/api/v1/admin/users/{new_id}?mode=full", headers=sa_headers)
    assert response2.status_code == 200

# 13. suite previa de usuarios inactivos sigue pasando
# Esto se valida corriendo tests completos, que ejecutarán test_auth_deactivated_users.py
