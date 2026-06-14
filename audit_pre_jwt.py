import sys
import json
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://proxvel_user:proxvel_password@localhost:5432/proxvel_db"
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        users = conn.execute(text("SELECT user_id, name, email, role, is_active FROM users ORDER BY user_id")).fetchall()
        
        profiles = conn.execute(text("SELECT user_id, COUNT(*) as cnt FROM traveler_profiles GROUP BY user_id")).fetchall()
        profile_map = {row[0]: row[1] for row in profiles}
        
        reviews = conn.execute(text("SELECT user_id, COUNT(*) as cnt FROM reviews GROUP BY user_id")).fetchall()
        review_map = {row[0]: row[1] for row in reviews}
        
        tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()
        table_names = [r[0] for r in tables]
        
        output = {
            "users": [{"user_id": u[0], "name": u[1], "email": u[2], "role": u[3], "is_active": u[4]} for u in users],
            "profiles": profile_map,
            "reviews": review_map,
            "tables": table_names
        }
        
        print(json.dumps(output, indent=2))
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
