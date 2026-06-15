import sys
import os
import io

# Añadir ruta del backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.config.database import SessionLocal
from app.models.user_model import User
from app.core.security import create_access_token
from fastapi.testclient import TestClient
from app.main import app

def get_or_create_user(db: Session, email: str, role: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            user_id=f"test_{role}_{os.urandom(4).hex()}",
            name=f"Test {role.capitalize()}",
            email=email,
            password_hash="fakehash123",
            role=role,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def ensure_destination_exists(db: Session, destination_id: str):
    from app.models.destination_model import Destination
    dest = db.query(Destination).filter(Destination.destination_id == destination_id).first()
    if not dest:
        dest = Destination(
            destination_id=destination_id,
            destination="Machu Picchu Test"
        )
        db.add(dest)
        db.commit()

def run_tests():
    db = SessionLocal()
    try:
        print("Configurando usuarios de prueba...")
        ensure_destination_exists(db, "machu-picchu")
        admin_user = get_or_create_user(db, "admin@proxvel.com", "admin")
        traveler_user = get_or_create_user(db, "traveler@proxvel.com", "traveler")
        
        admin_token = create_access_token({"sub": admin_user.user_id})
        traveler_token = create_access_token({"sub": traveler_user.user_id})
        
        client = TestClient(app)
        
        # 1. Caso Negativo: Traveler intenta subir
        print("\n1. Probando subida con rol traveler (Debe fallar con 403)...")
        # Usar la imagen del logo copiada
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_image.png")
        with open(image_path, "rb") as f:
            file_data = f.read()
        
        response = client.post(
            "/api/v1/destinations/machu-picchu/media/upload",
            headers={"Authorization": f"Bearer {traveler_token}"},
            data={"media_type": "cover", "alt_text": "Test"},
            files={"file": ("test.png", io.BytesIO(file_data), "image/png")}
        )
        print(f"Status: {response.status_code} - {response.json().get('detail')}")
        assert response.status_code == 403
        
        # 2. Caso Positivo: Admin intenta subir cover
        print("\n2. Probando subida de COVER con rol admin...")
        # NOTA: Esto intentará contactar a Cloudinary. Asegúrate de tener credenciales válidas en .env
        try:
            response = client.post(
                "/api/v1/destinations/machu-picchu/media/upload",
                headers={"Authorization": f"Bearer {admin_token}"},
                data={"media_type": "cover", "alt_text": "Machu Picchu Cover 1"},
                files={"file": ("test_cover1.png", io.BytesIO(file_data), "image/png")}
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("Exito! Cover 1 subida.")
                media_id_1 = response.json().get('media').get('id')
                
                print("\n2.5 Probando SEGUNDA COVER para desactivar la primera...")
                res_cov2 = client.post(
                    "/api/v1/destinations/machu-picchu/media/upload",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    data={"media_type": "cover", "alt_text": "Cover 2 Nueva"},
                    files={"file": ("test_cover2.png", io.BytesIO(file_data), "image/png")}
                )
                media_id_2 = res_cov2.json().get('media').get('id')
                
                print("\n2.6 Probando subida de GALLERY...")
                res_gal = client.post(
                    "/api/v1/destinations/machu-picchu/media/upload",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    data={"media_type": "gallery", "alt_text": "Galeria 1"},
                    files={"file": ("test_gal.png", io.BytesIO(file_data), "image/png")}
                )
                media_id_gal = res_gal.json().get('media').get('id')
                
                # 3. Consultar /media para validar cover
                print("\n3. Validando GET /media...")
                res_media = client.get("/api/v1/destinations/machu-picchu/media")
                media_data = res_media.json().get('data')
                print("Cover activa:", media_data.get('cover').get('url'))
                print("Items en gallery:", len(media_data.get('gallery', [])))
                
                # 4. PATCH
                print("\n4. Probando PATCH en gallery...")
                res_patch = client.patch(
                    f"/api/v1/destinations/machu-picchu/media/{media_id_gal}",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    json={"alt_text": "Galeria Editada"}
                )
                print(f"Status PATCH: {res_patch.status_code} - Alt text: {res_patch.json().get('media').get('alt_text')}")
                
                # 5. GET /destinations
                print("\n5. Validando GET /destinations...")
                res_dest = client.get("/api/v1/destinations")
                for d in res_dest.json().get('data', []):
                    if d.get('destination_id') == 'machu-picchu':
                        print("Cover image URL en catálogo:", d.get('cover_image_url'))
                
                # 6. DELETE (Soft delete) a Cover 2
                print("\n6. Probando DELETE en Cover 2...")
                res_del = client.delete(
                    f"/api/v1/destinations/machu-picchu/media/{media_id_2}",
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                print(f"Status DELETE: {res_del.status_code}")
                
                res_media_after = client.get("/api/v1/destinations/machu-picchu/media")
                print("Cover activa después de DELETE:", "Presente" if res_media_after.json().get('data').get('cover') else "Nulo")
                
            else:
                print("Fallo en la subida (Revisa credenciales Cloudinary):", response.json())
        except Exception as e:
            print("Error durante prueba E2E:", e)
            
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
