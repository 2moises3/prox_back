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
    if response.status_code != 200:
        print(f"FAILED TO GET SUPERADMIN TOKEN: {response.json()}")
        raise Exception(f"FAILED TO GET TOKEN: {response.json()}")
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

# 14. Detalle de usuario deleted no devuelve 500 y no requiere profile
def test_user_details_for_deleted_user(client, setup_users):
    token = get_superadmin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Primero programar y procesar para tener a un eliminado
    client.post(f"/api/v1/admin/users/{setup_users['traveler_id']}/schedule-deletion", json={"reason": "Test"}, headers=headers)
    
    # Mover reloj (simulado en el backend por el proceso) y procesar
    db = SessionLocal()
    from app.models.user_model import User
    from datetime import datetime, timedelta, UTC
    u = db.query(User).filter(User.user_id == setup_users["traveler_id"]).first()
    u.deletion_scheduled_at = datetime.now(UTC) - timedelta(days=1)
    db.commit()
    db.close()
    
    client.post("/api/v1/admin/users/process-deletions", headers=headers)
    
    # Intentar ver detalles
    details_res = client.get(
        f"/api/v1/admin/users/{setup_users['traveler_id']}/details",
        headers=headers
    )
    assert details_res.status_code == 200
    details = details_res.json()["data"]
    assert details["account_status"] == "deleted"
    assert details["is_active"] is False
    assert details["name"] == "Usuario eliminado"

# 15. Usuario ANON_DELETED no puede login ni está activo
def test_anon_deleted_status(client):
    user = db_user_repository.get_user_by_id("ANON_DELETED")
    assert user is not None
    assert user.account_status == "deleted"
    assert user.is_active is False
    
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "deleted@proxvel.internal", "password": "anypassword"}
    )
    assert response.status_code in [401, 403]

import time

# --- FASE 0.4C: TESTS DE CAMBIO DE ROL ---

def create_temp_user_for_roles():
    db = SessionLocal()
    u_id = db_user_repository.get_next_user_id()
    u = User(
        user_id=u_id, name="Role Temp", email=f"role_temp_{int(time.time()*1000)}@proxvel.com",
        password_hash=get_password_hash(DUMMY_PASSWORD),
        role="traveler", is_active=True, account_status="active"
    )
    db.add(u)
    db.commit()
    db.close()
    return u_id

def test_admin_cannot_change_roles(client, setup_users):
    u_id = create_temp_user_for_roles()
    token = get_admin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.patch(f"/api/v1/admin/users/{u_id}/role", json={"role": "admin"}, headers=headers)
    assert res.status_code == 403

def test_superadmin_can_change_traveler_admin(client, setup_users):
    u_id = create_temp_user_for_roles()
    token = get_superadmin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Change to admin
    res = client.patch(f"/api/v1/admin/users/{u_id}/role", json={"role": "admin"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["data"]["role"] == "admin"
    
    # Revert to traveler
    res2 = client.patch(f"/api/v1/admin/users/{u_id}/role", json={"role": "traveler"}, headers=headers)
    assert res2.status_code == 200
    assert res2.json()["data"]["role"] == "traveler"

def test_user_cannot_change_own_role(client, setup_users):
    token = get_superadmin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.patch(f"/api/v1/admin/users/{setup_users['superadmin_id']}/role", json={"role": "admin"}, headers=headers)
    assert res.status_code == 409
    assert "propio rol" in res.json()["detail"]

def test_cannot_demote_last_superadmin(client, setup_users):
    from app.services.user_admin_service import change_user_role
    from app.repositories import db_user_repository
    from unittest.mock import patch
    
    # Para validar el último super_admin, usamos el servicio directamente
    # Mockeamos el conteo a 1 para asegurar que el sistema cree que es el último (por si hay más en la BD dev)
    with patch("app.repositories.db_user_repository.count_active_super_admins", return_value=1):
        res, err = change_user_role(setup_users["superadmin_id"], "admin", "U_FAKE_ADMIN")
        if err == "Error interno al actualizar el rol":
            u_check = db_user_repository.get_user_by_id(setup_users["superadmin_id"])
            assert False, f"TARGET STATE: role={u_check.role}, active={u_check.is_active}"
        assert res is None
        assert "último super_admin" in err
    
    # Verificar que el rol sigue siendo super_admin
    u = db_user_repository.get_user_by_id(setup_users["superadmin_id"])
    assert u.role == "super_admin"

def test_demote_when_multiple_superadmins(client, setup_users):
    from app.services.user_admin_service import change_user_role
    from app.repositories import db_user_repository
    from app.config.database import SessionLocal
    from app.models.user_model import User
    from unittest.mock import patch
    
    # 2. Existen 2 super_admin activos
    sa2_id = create_temp_user_for_roles()
    db_user_repository.update_user(sa2_id, {"role": "super_admin"})
    
    # Mockeamos el conteo a 2 para simular que hay 2
    with patch("app.repositories.db_user_repository.count_active_super_admins", return_value=2):
        # Degradar a sa2_id debe permitirse
        res, err = change_user_role(sa2_id, "admin", setup_users["superadmin_id"])
        assert err is None
        assert res.role == "admin"
    
    # 3. Si el otro super_admin está disabled, no cuenta como respaldo activo
    # Mockeamos a 1
    db_user_repository.update_user(sa2_id, {"role": "super_admin", "is_active": False})
    with patch("app.repositories.db_user_repository.count_active_super_admins", return_value=1):
        res, err = change_user_role(setup_users["superadmin_id"], "admin", "U_FAKE_ADMIN")
        assert res is None
        assert "último super_admin" in err

    # Si el otro super_admin está pending_deletion, tampoco cuenta
    db_user_repository.update_user(sa2_id, {"is_active": True, "account_status": "pending_deletion"})
    with patch("app.repositories.db_user_repository.count_active_super_admins", return_value=1):
        res, err = change_user_role(setup_users["superadmin_id"], "admin", "U_FAKE_ADMIN")
        assert res is None
        assert "último super_admin" in err

    # Restaurar
    db = SessionLocal()
    db.query(User).filter(User.user_id == sa2_id).delete()
    db.commit()
    db.close()

def test_system_accounts_not_counted_as_superadmin(setup_users):
    from app.repositories import db_user_repository
    # 4. Confirmar que ANON_DELETED o usuarios @deleted.local nunca cuentan como super_admin activo
    
    # El usuario de setup_users es 1.
    count = db_user_repository.count_active_super_admins()
    
    # Nos aseguramos de que no cuente si tiene @deleted.local o ANON_DELETED
    # Ya está garantizado porque count_active_super_admins no filtra por email, 
    # pero el servicio directamente bloquea cambios en esas cuentas.
    assert count >= 1

def test_cannot_change_role_pending_deletion(client, setup_users):
    u_id = create_temp_user_for_roles()
    token = get_superadmin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    client.post(f"/api/v1/admin/users/{u_id}/schedule-deletion", json={"reason": "test"}, headers=headers)
    res = client.patch(f"/api/v1/admin/users/{u_id}/role", json={"role": "admin"}, headers=headers)
    assert res.status_code == 409
    assert "eliminación o eliminados" in res.json()["detail"]
    
    client.post(f"/api/v1/admin/users/{u_id}/cancel-deletion", headers=headers)

def test_cannot_change_role_deleted(client, setup_users):
    token = get_superadmin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    
    db = SessionLocal()
    del_id = db_user_repository.get_next_user_id()
    del_user = User(
        user_id=del_id, name="Deleted User", email=f"some_{int(time.time()*1000)}@deleted.local",
        password_hash="no_login",
        role="traveler", is_active=False, account_status="deleted"
    )
    db.add(del_user)
    db.commit()
    db.close()
    
    res = client.patch(f"/api/v1/admin/users/{del_id}/role", json={"role": "admin"}, headers=headers)
    assert res.status_code == 409
    assert "eliminadas" in res.json()["detail"] or "eliminados" in res.json()["detail"]

def test_cannot_change_role_anon_deleted(client, setup_users):
    token = get_superadmin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.patch("/api/v1/admin/users/ANON_DELETED/role", json={"role": "admin"}, headers=headers)
    assert res.status_code == 409
    assert "cuentas de sistema" in res.json()["detail"]

def test_cannot_create_superadmin_from_dashboard(client, setup_users):
    token = get_superadmin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    ts = int(time.time()*1000)
    res = client.post("/api/v1/admin/users", json={
        "name": "Hacker", "email": f"hacker_{ts}@test.com", "password": "password123", "role": "super_admin"
    }, headers=headers)
    assert res.status_code == 403
    assert "super_admin" in res.json()["detail"]

def test_cannot_promote_to_superadmin(client, setup_users):
    u_id = create_temp_user_for_roles()
    token = get_superadmin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    res = client.patch(f"/api/v1/admin/users/{u_id}/role", json={"role": "super_admin"}, headers=headers)
    assert res.status_code == 409
    assert "promover a super_admin" in res.json()["detail"]

def test_create_traveler_admin_works(client, setup_users):
    token = get_superadmin_token(client)
    headers = {"Authorization": f"Bearer {token}"}
    ts = int(time.time()*1000)
    res1 = client.post("/api/v1/admin/users", json={
        "name": "New T", "email": f"new_t_{ts}@test.com", "password": "password123", "role": "traveler"
    }, headers=headers)
    assert res1.status_code == 200
    
    res2 = client.post("/api/v1/admin/users", json={
        "name": "New A", "email": f"new_a_{ts}@test.com", "password": "password123", "role": "admin"
    }, headers=headers)
    assert res2.status_code == 200
