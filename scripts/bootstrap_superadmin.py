"""
PROXVEL Backend - Bootstrap Super Admin (Extensión 6B).

Script seguro para crear el primer super_admin del sistema.
Solo debe usarse como bootstrap inicial o en caso de emergencia.

Para crear admins/travelers operativos, usar el dashboard como super_admin.

Guardas de seguridad:
- Si ENVIRONMENT=production, se requiere ALLOW_SUPERADMIN_BOOTSTRAP=true.
- Si ya existe un super_admin activo, se muestra advertencia y se pide confirmación.
- No se acepta password por argumento (solo getpass o env var SUPERADMIN_PASSWORD).
- Se exige confirmación textual: CREATE_SUPERADMIN.
- No se expone password en logs.
"""

import os
import sys
import getpass

# Asegurar que el path sea correcto para importar desde app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.database import SessionLocal
from app.models.user_model import User
from app.utils.hash_util import get_password_hash
from app.repositories import db_user_repository


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║  ⚠️  PROXVEL — Bootstrap Super Admin                        ║
║                                                              ║
║  Este script crea un super_admin con control TOTAL           ║
║  del sistema. Solo usar para bootstrap inicial.              ║
║                                                              ║
║  Para crear admins/travelers, usar el dashboard.             ║
╚══════════════════════════════════════════════════════════════╝
"""


def main():
    print(BANNER)

    # ── Guarda de entorno ────────────────────────────────────────────────────
    environment = os.environ.get("ENVIRONMENT", "development").lower()
    if environment == "production":
        allow = os.environ.get("ALLOW_SUPERADMIN_BOOTSTRAP", "false").lower()
        if allow != "true":
            print("❌ BLOQUEADO: No se puede ejecutar en producción.")
            print("   Para permitirlo, establezca: ALLOW_SUPERADMIN_BOOTSTRAP=true")
            sys.exit(1)
        print("⚠️  Modo PRODUCCIÓN con ALLOW_SUPERADMIN_BOOTSTRAP=true")

    # ── Verificar super_admins existentes ────────────────────────────────────
    active_count = db_user_repository.count_active_super_admins()
    if active_count > 0:
        print(f"\n⚠️  Ya existe(n) {active_count} super_admin(s) activo(s) en el sistema.")
        print("   Crear otro super_admin solo es necesario en caso de emergencia.")
        proceed = input("   ¿Desea continuar? [s/N]: ").strip().lower()
        if proceed != "s":
            print("Operación cancelada.")
            sys.exit(0)

    # ── Recoger datos ────────────────────────────────────────────────────────
    email = input("\nEmail del super_admin: ").strip()
    if not email or "@" not in email:
        print("❌ Email inválido.")
        sys.exit(1)

    name = input("Nombre completo: ").strip()
    if not name:
        print("❌ Nombre requerido.")
        sys.exit(1)

    # Password: desde env var o getpass (NUNCA como argumento de CLI)
    password = os.environ.get("SUPERADMIN_PASSWORD")
    if password:
        print("🔑 Password tomado de variable de entorno SUPERADMIN_PASSWORD.")
    else:
        password = getpass.getpass("Contraseña: ")
        confirm_password = getpass.getpass("Confirmar contraseña: ")
        if password != confirm_password:
            print("❌ Las contraseñas no coinciden.")
            sys.exit(1)

    if len(password) < 6:
        print("❌ La contraseña debe tener al menos 6 caracteres.")
        sys.exit(1)

    # ── Confirmación textual ─────────────────────────────────────────────────
    print(f"\n🔴 Se creará un SUPER_ADMIN con:")
    print(f"   Email: {email}")
    print(f"   Nombre: {name}")
    print(f"   Rol: super_admin (CONTROL TOTAL)")
    confirm = input("\n   Escriba CREATE_SUPERADMIN para confirmar: ").strip()
    if confirm != "CREATE_SUPERADMIN":
        print("Operación cancelada.")
        sys.exit(0)

    # ── Crear o actualizar ───────────────────────────────────────────────────
    hashed_password = get_password_hash(password)

    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == email).first()

        if existing_user:
            existing_user.name = name
            existing_user.role = "super_admin"
            existing_user.password_hash = hashed_password
            existing_user.is_active = True
            db.commit()
            db.refresh(existing_user)
            print(f"\n✅ Usuario '{name}' ({email}) actualizado a super_admin.")
        else:
            new_user_id = db_user_repository.get_next_user_id()
            new_user = User(
                user_id=new_user_id,
                name=name,
                email=email,
                password_hash=hashed_password,
                role="super_admin",
                is_active=True,
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            print(f"\n✅ Super_admin '{name}' ({email}) creado con ID {new_user_id}.")

        print("   ⚠️  Guarde las credenciales de forma segura. No se mostrarán de nuevo.")

    except Exception as e:
        print(f"❌ Error interno: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
