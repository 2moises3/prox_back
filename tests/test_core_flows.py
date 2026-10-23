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
    "perfil_turistico": "naturalista",
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


def test_motor_usa_tipo_explicito(client):
    perfil = client.get(f"{API}/users/{VIAJERO}/traveler-profile", headers=h()).json()["data"]
    assert perfil["perfil_turistico"] == "naturalista"
    from app.services.thesis_engine import get_engine
    assert list(get_engine().components(perfil)["weights"]) == [.25, .30, .45]


def test_presupuesto_dias_y_sliders_no_cambian_v3():
    from app.services.thesis_engine import get_engine
    import numpy as np
    engine = get_engine()
    a = engine.components(PERFIL)
    b = engine.components({**PERFIL, "presupuesto":"bajo", "dias_viaje":30, "peso_costos":5})
    np.testing.assert_array_equal(a['scores'], b['scores'])


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
    assert body["engine"]["source"] == "tesis_v3"
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


@pytest.mark.parametrize('month', [1,4,7,10])
def test_api_v3_reproduce_nucleo_sin_recortar_scores(client, month):
    from app.services.thesis_engine import get_engine
    actual = client.get(f'{API}/recommendations/me',params={'limit':100,'month':month},headers=h())
    assert actual.status_code == 200, actual.text
    reference = get_engine().recommend(PERFIL,month,14)
    rows = actual.json()['data']
    assert [r['destination_id'] for r in rows] == [r['destination_id'] for r in reference]
    for a,b in zip(rows,reference):
        assert a['compatibility_score'] == b['compatibility_score']
        assert a['compatibility_percent'] == b['compatibility_percent']
        assert a['label_code'] == b['label']
        assert a['explanation']['shap_values'] == b['explanation']['shap_values']


def test_perfil_antiguo_requiere_estilo_explicito(client):
    from app.models.traveler_profile_model import TravelerProfile
    with SessionLocal() as db:
        profile = db.query(TravelerProfile).filter_by(user_id=VIAJERO).one()
        profile.perfil_turistico = None
        db.commit()
    response = client.get(f'{API}/recommendations/me',headers=h())
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'TRAVELER_PROFILE_INCOMPLETE'
    assert client.patch(f'{API}/users/{VIAJERO}/traveler-profile',json={'perfil_turistico':'naturalista'},headers=h()).status_code == 200
