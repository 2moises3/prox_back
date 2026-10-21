"""
Flujos principales del viajero: perfil → recomendaciones (motor de la tesis), favoritos y archivados.
Necesita los datos de `python scripts/seed_from_thesis.py`; si la BD está vacía se omite.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.config.database import SessionLocal
from app.core.security import create_access_token
from app.models.destination_model import Destination
from app.models.user_model import User
from app.services import recommendation_engine_v1 as engine
from app.utils.hash_util import get_password_hash

API = "/api/v1"
VIAJERO = "ZFLOW_TRAV"
OTRO = "ZFLOW_OTRO"
DEST = "chan_chan"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _purge(db):
    for uid in (VIAJERO, OTRO):
        tablas = [t for (t,) in db.execute(text(
            "select table_name from information_schema.columns "
            "where column_name='user_id' and table_schema='public' and table_name <> 'users'"))]
        for t in tablas:
            db.execute(text(f'delete from "{t}" where user_id = :u'), {"u": uid})
        db.query(User).filter_by(user_id=uid).delete()
    db.commit()


@pytest.fixture(scope="module", autouse=True)
def usuarios():
    db = SessionLocal()
    if db.query(Destination).filter_by(destination_id=DEST).first() is None:
        db.close()
        pytest.skip("BD sin datos: ejecuta scripts/seed_from_thesis.py")
    _purge(db)
    for uid in (VIAJERO, OTRO):
        db.add(User(user_id=uid, name=uid, email=f"{uid.lower()}@mailinator.com",
                    password_hash=get_password_hash("ClaveSegura123"), role="traveler",
                    is_active=True, account_status="active", residence_department="LIMA"))
    db.commit()
    yield
    _purge(db)
    db.close()


def h(uid=VIAJERO):
    return {"Authorization": f"Bearer {create_access_token(data={'sub': uid, 'role': 'traveler'})}"}


PERFIL = {
    "intereses": ["naturaleza", "aventura", "montanismo"],
    "clima_preferido": "frio",
    "tolerancia_multitudes": "baja",
    "presupuesto": "alto",
}


# ── Perfil del viajero ────────────────────────────────────────────────────────

def test_recomendaciones_exigen_perfil(client):
    r = client.get(f"{API}/recommendations/me", headers=h())
    assert r.status_code == 400
    assert "Onboarding" in r.json()["detail"]


def test_perfil_solo_lo_ve_y_edita_su_dueno(client):
    assert client.get(f"{API}/users/{VIAJERO}/traveler-profile", headers=h(OTRO)).status_code == 403
    assert client.put(f"{API}/users/{VIAJERO}/traveler-profile", json=PERFIL, headers=h(OTRO)).status_code == 403
    assert client.get(f"{API}/users/{VIAJERO}/traveler-profile").status_code == 401


def test_patch_sin_perfil_previo_es_404(client):
    r = client.patch(f"{API}/users/{VIAJERO}/traveler-profile", json={"apply_ai_globally": True}, headers=h())
    assert r.status_code == 404


def test_guardar_perfil_no_inventa_pesos(client):
    r = client.put(f"{API}/users/{VIAJERO}/traveler-profile", json=PERFIL, headers=h())
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["intereses"] == PERFIL["intereses"]
    # El backend no deriva pesos: quedan sin valor o neutros.
    pesos = {data.get(f"peso_{a}") for a in ("limpieza", "atencion_servicio", "atractivos")}
    assert pesos <= {None, 3.0}


def test_motor_usa_pesos_de_la_tesis_por_tipo_de_viajero(client):
    perfil = client.get(f"{API}/users/{VIAJERO}/traveler-profile", headers=h()).json()["data"]
    intereses = {engine._norm(i) for i in perfil["intereses"]}
    # naturaleza + montañismo → naturalista (2 votos) le gana a aventurero (1)
    assert engine._pesos_calidad(perfil, intereses) == engine._PESOS_POR_PERFIL["naturalista"]


def test_sliders_explicitos_si_se_respetan():
    perfil = {"peso_limpieza": 5.0, "peso_atencion_servicio": 1.0, "peso_atractivos": 4.0}
    w = engine._pesos_calidad(perfil, set())
    assert w == {"limpieza": 0.5, "atencion_servicio": 0.1, "atractivos": 0.4}


def test_patch_parcial_conserva_lo_demas(client):
    r = client.patch(f"{API}/users/{VIAJERO}/traveler-profile", json={"apply_ai_globally": True}, headers=h())
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["apply_ai_globally"] is True
    assert data["intereses"] == PERFIL["intereses"]
    assert data["tolerancia_multitudes"] == "baja"


# ── Recomendaciones ───────────────────────────────────────────────────────────

def test_recomendaciones_del_motor(client):
    r = client.get(f"{API}/recommendations/me", params={"limit": 14, "month": 7}, headers=h())
    assert r.status_code == 200, r.text
    body = r.json()
    items = body["data"]
    assert body["engine"]["source"] == "engine_v1"
    assert 1 <= len(items) <= 14
    ids = [i["destination_id"] for i in items]
    assert len(ids) == len(set(ids))
    with SessionLocal() as db:
        en_motor = {d.destination_id for d in db.query(Destination).filter_by(in_engine=True, is_active=True)}
    assert set(ids) <= en_motor, "solo se recomiendan destinos que participan en el motor"


def test_mes_invalido_y_limite(client):
    assert client.get(f"{API}/recommendations/me", params={"month": 13}, headers=h()).status_code == 422
    r = client.get(f"{API}/recommendations/me", params={"limit": 3}, headers=h())
    assert len(r.json()["data"]) <= 3


def test_admin_no_tiene_recomendaciones(client):
    tok = create_access_token(data={"sub": "U00001", "role": "super_admin"})
    with SessionLocal() as db:
        if db.query(User).filter_by(user_id="U00001").first() is None:
            pytest.skip("sin super_admin en la BD")
    r = client.get(f"{API}/recommendations/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 403


# ── Favoritos y archivados ────────────────────────────────────────────────────

def test_favoritos(client):
    assert client.get(f"{API}/favorites/check/{DEST}", headers=h()).json()["data"]["is_favorite"] is False
    assert client.post(f"{API}/favorites/{DEST}", headers=h()).status_code in (200, 201)
    # Repetir no duplica
    client.post(f"{API}/favorites/{DEST}", headers=h())
    lista = client.get(f"{API}/favorites", headers=h()).json()["data"]
    assert [f["destination_id"] for f in lista].count(DEST) == 1
    assert client.get(f"{API}/favorites/check/{DEST}", headers=h()).json()["data"]["is_favorite"] is True
    # Son de cada viajero
    assert client.get(f"{API}/favorites", headers=h(OTRO)).json()["data"] == []
    assert client.delete(f"{API}/favorites/{DEST}", headers=h()).status_code == 200
    assert client.get(f"{API}/favorites/check/{DEST}", headers=h()).json()["data"]["is_favorite"] is False


def test_favorito_de_destino_inexistente(client):
    assert client.post(f"{API}/favorites/no_existe", headers=h()).status_code in (400, 404)


def test_favoritos_exigen_sesion(client):
    assert client.get(f"{API}/favorites").status_code == 401


def test_archivados(client):
    assert client.post(f"{API}/archives/{DEST}", headers=h()).status_code in (200, 201)
    lista = client.get(f"{API}/archives", headers=h()).json()["data"]
    assert DEST in [a["destination_id"] for a in lista]
    assert client.delete(f"{API}/archives/{DEST}", headers=h()).status_code == 200
    assert DEST not in [a["destination_id"] for a in client.get(f"{API}/archives", headers=h()).json()["data"]]


def test_siguiente_id_ignora_ids_no_numericos():
    # Este módulo crea usuarios ZFLOW_* (IDs no numéricos) y siempre existe ANON_DELETED.
    from app.repositories.db_user_repository import get_next_user_id
    nuevo = get_next_user_id()
    assert nuevo.startswith("U") and nuevo[1:].isdigit()
    with SessionLocal() as db:
        assert db.query(User).filter_by(user_id=nuevo).first() is None, "no debe repetir un ID existente"
