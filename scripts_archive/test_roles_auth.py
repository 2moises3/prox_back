import os
import sys

# Ensure path is correct
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.config.database import SessionLocal
from app.models.user_model import User
from app.models.destination_model import Destination
from app.utils.hash_util import get_password_hash
from app.core.security import create_access_token
import time

client = TestClient(app)

def get_or_create_user(db, email: str, role: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            user_id=f"test_{role}_{int(time.time())}",
            name=f"Test {role}",
            email=email,
            password_hash=get_password_hash("testpassword"),
            role=role,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def ensure_destination_exists(db, destination_id: str):
    dest = db.query(Destination).filter(Destination.destination_id == destination_id).first()
    if not dest:
        dest = Destination(
            destination_id=destination_id,
            destination="Test Destination"
        )
        db.add(dest)
        db.commit()

def run_tests():
    db = SessionLocal()
    try:
        print("Configurando base de datos para testing de roles...")
        traveler = get_or_create_user(db, "traveler_test@proxvel.com", "traveler")
        admin = get_or_create_user(db, "admin_test@proxvel.com", "admin")
        super_admin = get_or_create_user(db, "super_admin_test@proxvel.com", "super_admin")
        
        ensure_destination_exists(db, "machu-picchu")

        traveler_token = create_access_token({"sub": traveler.user_id, "email": traveler.email})
        admin_token = create_access_token({"sub": admin.user_id, "email": admin.email})
        super_admin_token = create_access_token({"sub": super_admin.user_id, "email": super_admin.email})

        print("\n--- TEST: TRAVELER ---")
        # 1. Traveler no puede subir media
        headers = {"Authorization": f"Bearer {traveler_token}"}
        res = client.post("/api/v1/destinations/machu-picchu/media/upload", headers=headers)
        print(f"POST /media con traveler -> Status: {res.status_code} (Esperado 403)")
        assert res.status_code == 403

        # 2. Traveler puede pedir recommendations/me (pero debe dar 400 por falta de perfil)
        res = client.get("/api/v1/recommendations/me", headers=headers)
        print(f"GET /recommendations/me con traveler (sin perfil) -> Status: {res.status_code} (Esperado 400)")
        assert res.status_code == 400

        print("\n--- TEST: ADMIN ---")
        # 3. Admin puede subir media (Esperamos 500 o ValidationError si falta imagen, pero NO 403)
        headers = {"Authorization": f"Bearer {admin_token}"}
        res = client.post("/api/v1/destinations/machu-picchu/media/upload", headers=headers)
        print(f"POST /media con admin -> Status: {res.status_code} (Esperado != 403)")
        assert res.status_code != 403

        # 4. Admin obtiene 403 en recommendations/me por no ser traveler (nuevo comportamiento pedido)
        res = client.get("/api/v1/recommendations/me", headers=headers)
        print(f"GET /recommendations/me con admin (sin perfil) -> Status: {res.status_code} (Esperado 403)")
        assert res.status_code == 403

        print("\n--- TEST: SUPER_ADMIN ---")
        # 5. Super Admin puede subir media
        headers = {"Authorization": f"Bearer {super_admin_token}"}
        res = client.post("/api/v1/destinations/machu-picchu/media/upload", headers=headers)
        print(f"POST /media con super_admin -> Status: {res.status_code} (Esperado != 403)")
        assert res.status_code != 403
        
        # 6. Super Admin obtiene 403 en recommendations/me por no ser traveler
        res = client.get("/api/v1/recommendations/me", headers=headers)
        print(f"GET /recommendations/me con super_admin (sin perfil) -> Status: {res.status_code} (Esperado 403)")
        assert res.status_code == 403

        print("\nTodos los tests pasaron exitosamente.")

    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
