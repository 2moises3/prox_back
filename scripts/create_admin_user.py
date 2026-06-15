import os
import sys
import argparse
import getpass

# Asegurar que el path sea correcto para importar desde app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import SessionLocal
from app.models.user_model import User
from app.utils.hash_util import get_password_hash
from app.repositories import db_user_repository

def main():
    parser = argparse.ArgumentParser(description="Crear usuario administrativo")
    parser.add_argument("--email", type=str, help="Email del administrador")
    parser.add_argument("--name", type=str, help="Nombre del administrador")
    parser.add_argument("--role", type=str, choices=["admin", "super_admin"], help="Rol (admin o super_admin)")
    
    args = parser.parse_args()

    email = args.email or input("Email: ").strip()
    name = args.name or input("Nombre: ").strip()
    role = args.role
    
    while role not in ["admin", "super_admin"]:
        role = input("Rol [admin/super_admin]: ").strip()

    password = getpass.getpass("Contraseña: ")
    confirm_password = getpass.getpass("Confirmar contraseña: ")

    if password != confirm_password:
        print("Error: Las contraseñas no coinciden.")
        sys.exit(1)

    if len(password) < 6:
        print("Error: La contraseña debe tener al menos 6 caracteres.")
        sys.exit(1)

    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"Error: El email {email} ya está registrado.")
            sys.exit(1)

        new_user_id = db_user_repository.get_next_user_id()
        hashed_password = get_password_hash(password)

        new_user = User(
            user_id=new_user_id,
            name=name,
            email=email,
            password_hash=hashed_password,
            role=role,
            is_active=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"Éxito: Usuario '{name}' ({email}) creado con rol '{role}'.")

    except Exception as e:
        print(f"Error interno: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
