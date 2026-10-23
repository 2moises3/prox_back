"""
Importadores del dashboard con los CSV reales de la tesis (seed_data/).
Reimportar los mismos datos no debe cambiar nada (idempotente) ni crear destinos nuevos.
Necesita los datos de `python scripts/seed_from_thesis.py`; si la BD está vacía se omite.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.config.database import SessionLocal
from app.core.security import create_access_token
from app.models.destination_model import Destination
from app.models.user_model import User
from app.utils.hash_util import get_password_hash

API = "/api/v1"
ADMIN = "ZIMP_ADMIN"
SEED = Path(__file__).resolve().parent.parent / "seed_data"

FILES = {
    "absa": "matriz_destino_aspecto_sentimiento.csv",
    "tags": "registro_maestro_centros_turisticos.csv",
    "clima": "clima_scores.csv",
    "aforo": "aforo_scores.csv",
}

SNAPSHOT_SQL = {
    "absa": (
        "select destination_id, round(cast(limpieza as numeric), 6), round(cast(atencion_servicio as numeric), 6), "
        "round(cast(atractivos as numeric), 6) from destination_aspect_scores order by 1"
    ),
    "tags": "select destination_id, tag from destination_tags order by 1, 2",
    "contexto": (
        "select destination_id, month, cast(clima_por_preferencia as text), cast(aforo_por_tolerancia as text) "
        "from destination_month_context order by 1, 2"
    ),
    "destinos": "select destination_id, is_active, in_engine from destinations order by 1",
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def admin():
    db = SessionLocal()
    if db.query(Destination).count() == 0 or not all((SEED / f).exists() for f in FILES.values()):
        db.close()
        pytest.skip("BD o CSV de la tesis no disponibles")
    db.query(User).filter_by(user_id=ADMIN).delete()
    db.add(User(user_id=ADMIN, name=ADMIN, email="zimp.admin@mailinator.com",
                password_hash=get_password_hash("ClaveSegura123"), role="admin",
                is_active=True, account_status="active"))
    db.commit()
    yield
    db.query(User).filter_by(user_id=ADMIN).delete()
    db.commit()
    db.close()


def h():
    return {"Authorization": f"Bearer {create_access_token(data={'sub': ADMIN, 'role': 'admin'})}"}


def snapshot() -> dict:
    with SessionLocal() as db:
        out = {}
        for k, sql in SNAPSHOT_SQL.items():
            try:
                out[k] = [tuple(r) for r in db.execute(text(sql))]
            except Exception as e:
                raise AssertionError(f"no se pudo leer {k}: {e}")
        return out


def upload(client, kind, content: bytes, name="datos.csv"):
    return client.post(f"{API}/admin/import/{kind}", files={"file": (name, content, "text/csv")}, headers=h())


def test_reimportar_la_tesis_no_cambia_nada(client):
    antes = snapshot()
    for kind, fname in FILES.items():
        r = upload(client, kind, (SEED / fname).read_bytes(), fname)
        assert r.status_code == 409, f"{kind}: {r.text}"
    despues = snapshot()
    for k in SNAPSHOT_SQL:
        assert antes[k], f"sin datos de {k} para comparar"
        assert despues[k] == antes[k], f"reimportar cambió {k}"


def test_tipo_archivo_y_contenido_invalidos(client):
    assert upload(client, "otro", b"a,b\n1,2").status_code == 400
    assert upload(client, "absa", b"a,b\n1,2", name="datos.pdf").status_code == 400
    assert upload(client, "absa", b"PK\x03\x04 no es un excel", name="datos.xlsx").status_code == 409
    assert upload(client, "absa", b"   ").status_code == 400
    r = upload(client, "clima", b"columna_rara,otra\n1,2\n")
    assert r.status_code == 409


def test_importar_exige_admin(client):
    tok = create_access_token(data={"sub": "nadie", "role": "traveler"})
    r = client.post(f"{API}/admin/import/absa", files={"file": ("a.csv", b"a\n1", "text/csv")},
                    headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code in (401, 403)
