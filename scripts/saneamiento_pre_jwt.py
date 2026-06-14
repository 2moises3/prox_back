import sys
import argparse
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://proxvel_user:proxvel_password@localhost:5432/proxvel_db"
WHITELIST = ('U00001', 'U00002', 'U00003')
WHITELIST_STR = "','".join(WHITELIST)

def main():
    parser = argparse.ArgumentParser(description="Script de saneamiento de usuarios pre-JWT")
    parser.add_argument("--execute", action="store_true", help="Ejecutar la eliminación real de la base de datos")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar qué se va a eliminar sin afectar la base de datos (por defecto)")
    args = parser.parse_args()

    # Si no hay --execute, forzamos dry-run
    is_dry_run = not args.execute

    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # 1. Usuarios a conservar
            print("=== USUARIOS WHITELIST (A CONSERVAR) ===")
            conservados = conn.execute(text(f"SELECT user_id, email FROM users WHERE user_id IN ('{WHITELIST_STR}') ORDER BY user_id")).fetchall()
            for u in conservados:
                print(f" - {u[0]}: {u[1]}")

            # 2. Usuarios candidatos a eliminar
            print("\n=== USUARIOS CANDIDATOS A ELIMINAR ===")
            candidatos = conn.execute(text(f"SELECT user_id, email FROM users WHERE user_id NOT IN ('{WHITELIST_STR}') ORDER BY user_id")).fetchall()
            for c in candidatos:
                print(f" - {c[0]}: {c[1]}")
            
            if not candidatos:
                print("No hay usuarios para eliminar.")
                return

            not_in_clause = f"NOT IN ('{WHITELIST_STR}')"

            # 3. Conteo de registros a eliminar
            print("\n=== CONTEO DE REGISTROS A ELIMINAR POR TABLA ===")
            
            q_rar = f"""
                SELECT COUNT(*) FROM review_aspect_ratings 
                WHERE review_id IN (
                    SELECT review_id FROM reviews WHERE user_id {not_in_clause}
                )
            """
            count_rar = conn.execute(text(q_rar)).scalar()
            print(f" - review_aspect_ratings: {count_rar}")
            
            count_rev = conn.execute(text(f"SELECT COUNT(*) FROM reviews WHERE user_id {not_in_clause}")).scalar()
            print(f" - reviews: {count_rev}")
            
            count_fav = conn.execute(text(f"SELECT COUNT(*) FROM favorites WHERE user_id {not_in_clause}")).scalar()
            print(f" - favorites: {count_fav}")
            
            count_prof = conn.execute(text(f"SELECT COUNT(*) FROM traveler_profiles WHERE user_id {not_in_clause}")).scalar()
            print(f" - traveler_profiles: {count_prof}")
            
            count_user = conn.execute(text(f"SELECT COUNT(*) FROM users WHERE user_id {not_in_clause}")).scalar()
            print(f" - users: {count_user}")

            if is_dry_run:
                print("\n" + "="*50)
                print("MODO DRY-RUN: no se eliminó ningún dato.")
                print("==================================================")
                print("NOTA: Se recomienda hacer un backup/export SQL (ej. pg_dump) antes de ejecutar el modo --execute.")
            else:
                print("\n=== MODO EXECUTE: Iniciando transacción ===")
                # Eliminar en orden seguro
                conn.execute(text(f"DELETE FROM review_aspect_ratings WHERE review_id IN (SELECT review_id FROM reviews WHERE user_id {not_in_clause})"))
                conn.execute(text(f"DELETE FROM reviews WHERE user_id {not_in_clause}"))
                conn.execute(text(f"DELETE FROM favorites WHERE user_id {not_in_clause}"))
                conn.execute(text(f"DELETE FROM traveler_profiles WHERE user_id {not_in_clause}"))
                conn.execute(text(f"DELETE FROM users WHERE user_id {not_in_clause}"))
                
                # SQLAlchemy 2.0 requires manual commit
                conn.commit()
                
                print("Transacción exitosa. Commit realizado.")
                
                print("\n=== CONTEO FINAL ===")
                count_final = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
                print(f"Usuarios restantes en BD: {count_final}")
                final_users = conn.execute(text("SELECT user_id FROM users ORDER BY user_id")).fetchall()
                for fu in final_users:
                    print(f" - {fu[0]}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if not is_dry_run:
            print("Transacción revertida (Rollback).", file=sys.stderr)

if __name__ == "__main__":
    main()
