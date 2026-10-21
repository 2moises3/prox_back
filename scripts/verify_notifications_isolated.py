"""Run notification integration tests in a disposable, isolated PostgreSQL database.

Uses the configured server credentials without printing them. Never points pytest
at the application's database; only this run's random database is removed.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config.settings import get_settings


def main():
    configured = make_url(get_settings().DATABASE_URL)
    if configured.get_backend_name() != "postgresql":
        raise RuntimeError("This verification requires PostgreSQL")
    name = "proxvel_notif_test_" + uuid.uuid4().hex[:12]
    if not re.fullmatch(r"proxvel_notif_test_[0-9a-f]{12}", name) or name == configured.database:
        raise RuntimeError("Invalid isolated database name")
    admin = create_engine(configured.set(database="postgres"), isolation_level="AUTOCOMMIT")
    created = False
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
            created = True
        env = dict(os.environ)
        env["DATABASE_URL"] = configured.set(database=name).render_as_string(hide_password=False)
        env["ENABLE_BACKGROUND_JOBS"] = "false"
        env["SQL_ECHO"] = "false"
        env["DEBUG"] = "false"
        env["PROXVEL_ISOLATED_NOTIFICATIONS_TEST"] = "1"
        root = Path(__file__).resolve().parents[1]
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root, env=env, check=True)
        print("Testing notifications in an isolated database.", flush=True)
        subprocess.run([sys.executable, "-m", "pytest", "tests/test_notifications.py", "-q"], cwd=root, env=env, check=True)
    finally:
        if created:
            with admin.connect() as connection:
                connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
            print("Isolated notification database removed.", flush=True)
        admin.dispose()


if __name__ == "__main__":
    main()
