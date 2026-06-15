import os
import sys
import argparse

# Asegurar que el path sea correcto para importar desde app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import SessionLocal
from app.models.user_model import User

def main():
    parser = argparse.ArgumentParser(description="Migrar rol 'user' a 'traveler'")
    parser.add_argument("--execute", action="store_true", help="Ejecutar la migración (si no se envía, corre en dry-run mode)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        users = db.query(User).filter(User.role == "user").all()
        
        print(f"=== MIGRACIÓN DE ROLES ('user' -> 'traveler') ===")
        print(f"Usuarios encontrados con rol 'user': {len(users)}")
        
        if not args.execute:
            print("\nModo DRY-RUN activado. No se realizarán cambios en la base de datos.")
            print("Para ejecutar la migración, usa el flag --execute.")
            sys.exit(0)

        count = 0
        for user in users:
            user.role = "traveler"
            count += 1
            
        db.commit()
        print(f"\nÉxito: {count} usuarios migrados a 'traveler'.")

    except Exception as e:
        print(f"Error interno: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
