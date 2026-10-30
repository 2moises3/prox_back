"""
PROXVEL Backend - Tests de Geolocalización, Check-in y Atlas de Visitas.
Valida el cálculo de radio Haversine, registro de check-in, permanencia mínima y sellado de visitas.
"""
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config.database import get_db
from app.main import app
from app.models.base import Base
from app.models.destination_model import Destination
from app.models.tourism_catalog_model import TourismCatalog
from app.models.user_model import User
from app.models.visit_model import Visit
from app.services.visit_service import (
    check_in_visit,
    get_active_visit,
    get_user_atlas,
    haversine_distance_meters,
    verify_visit,
)

# Base de datos SQLite in-memory para aislamiento total
TEST_SQL_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_SQL_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


from app.core.security import create_access_token, get_current_user
from app.schemas.user_schema import UserResponse

def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    return UserResponse(
        id=1,
        user_id="U_VISIT_TEST",
        email="visit_test@proxvel.local",
        name="Viajero Test",
        role="traveler",
        account_status="active",
        is_active=True,
    )


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    Base.metadata.create_all(bind=test_engine)
    db = TestingSession()

    # Usuario de prueba
    user = User(
        user_id="U_VISIT_TEST",
        email="visit_test@proxvel.local",
        name="Viajero Test",
        role="traveler",
        account_status="active",
        is_active=True,
        password_hash="fakehashdummy12345",
    )
    user2 = User(
        user_id="U_OTHER_TEST",
        email="other_test@proxvel.local",
        name="Otro Viajero",
        role="traveler",
        account_status="active",
        is_active=True,
        password_hash="fakehashdummy12345",
    )
    db.add(user)
    db.add(user2)

    # Destino 1: Circuito Mágico del Agua (Lima) con radio 250m y tiempo 20 min
    d1 = Destination(destination_id="circuito_magico", destination="Circuito Mágico del Agua", in_engine=True)
    c1 = TourismCatalog(
        destination_id="circuito_magico",
        latitude=-12.0694,
        longitude=-77.0346,
        region="LIMA",
        city="Lima",
        category="Parques y Jardines",
        geofence_radius_meters=250,
        min_dwell_minutes=20,
    )
    db.add(d1)
    db.add(c1)

    # Destino 2: Sin coordenadas
    d2 = Destination(destination_id="destino_sin_coords", destination="Destino Misterioso", in_engine=False)
    c2 = TourismCatalog(
        destination_id="destino_sin_coords",
        latitude=None,
        longitude=None,
        region="CUSCO",
    )
    db.add(d2)
    db.add(c2)

    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest.fixture
def db_session():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def auth_header(user_id: str = "U_VISIT_TEST") -> dict:
    token = create_access_token(data={"sub": user_id})
    return {"Authorization": f"Bearer {token}"}


# ==========================================
# 1. Pruebas Unitarias de Haversine
# ==========================================
def test_haversine_same_point():
    d = haversine_distance_meters(-12.0694, -77.0346, -12.0694, -77.0346)
    assert d == 0.0


def test_haversine_short_distance():
    # Desplazamiento aproximado de ~100 metros
    d = haversine_distance_meters(-12.0694, -77.0346, -12.0700, -77.0346)
    assert 60.0 < d < 80.0


# ==========================================
# 2. Pruebas Unitarias del Servicio de Visitas
# ==========================================
def test_check_in_destination_not_found(db_session):
    result, error, code = check_in_visit(
        user_id="U_VISIT_TEST",
        destination_id="no_existe",
        latitude=-12.0694,
        longitude=-77.0346,
        db=db_session,
    )
    assert result is None
    assert code == 404
    assert "no encontrado" in error


def test_check_in_destination_missing_coords(db_session):
    result, error, code = check_in_visit(
        user_id="U_VISIT_TEST",
        destination_id="destino_sin_coords",
        latitude=-12.0694,
        longitude=-77.0346,
        db=db_session,
    )
    assert result is None
    assert code == 422
    assert "coordenadas" in error


def test_check_in_user_outside_geofence(db_session):
    # El usuario está en Miraflores (-12.1215, -77.0298), a ~5.8 km del Circuito Mágico
    result, error, code = check_in_visit(
        user_id="U_VISIT_TEST",
        destination_id="circuito_magico",
        latitude=-12.1215,
        longitude=-77.0298,
        db=db_session,
    )
    assert result is None
    assert code == 422
    assert "Debes estar a menos de" in error


def test_check_in_success_inside_geofence(db_session):
    # El usuario está exactamente a 50m del centro (-12.0694, -77.0346)
    result, error, code = check_in_visit(
        user_id="U_VISIT_TEST",
        destination_id="circuito_magico",
        latitude=-12.0694,
        longitude=-77.0346,
        db=db_session,
    )
    assert error is None
    assert code == 201
    assert result["visit_status"] == "in_progress"
    assert result["min_dwell_minutes"] == 20
    assert result["remaining_minutes"] == 20
    assert result["destination_name"] == "Circuito Mágico del Agua"


def test_check_in_idempotent_existing_visit(db_session):
    # Segundo check-in mientras la visita sigue activa
    result, error, code = check_in_visit(
        user_id="U_VISIT_TEST",
        destination_id="circuito_magico",
        latitude=-12.0694,
        longitude=-77.0346,
        db=db_session,
    )
    assert error is None
    assert code == 200  # 200 porque recupera la sesión activa existente
    assert result["visit_status"] == "in_progress"


def test_verify_visit_premature(db_session):
    active = get_active_visit("U_VISIT_TEST", db=db_session)
    assert active is not None
    vid = active["visit_id"]

    # Intentar certificar de inmediato (0 minutos transcurridos de 20 mínimos)
    result, error, code = verify_visit(
        user_id="U_VISIT_TEST",
        visit_id=vid,
        latitude=-12.0694,
        longitude=-77.0346,
        db=db_session,
    )
    assert result is None
    assert code == 422
    assert "Aún faltan" in error


def test_verify_visit_forbidden_user(db_session):
    active = get_active_visit("U_VISIT_TEST", db=db_session)
    vid = active["visit_id"]

    # Otro usuario intenta certificar la visita
    result, error, code = verify_visit(
        user_id="U_OTHER_TEST",
        visit_id=vid,
        latitude=-12.0694,
        longitude=-77.0346,
        db=db_session,
    )
    assert result is None
    assert code == 403


def test_verify_visit_success_after_dwell(db_session):
    # Simulamos que el started_at fue hace 25 minutos
    visit = db_session.query(Visit).filter(Visit.user_id == "U_VISIT_TEST").first()
    past_time = datetime.now(timezone.utc) - timedelta(minutes=25)
    visit.started_at = past_time
    db_session.commit()

    result, error, code = verify_visit(
        user_id="U_VISIT_TEST",
        visit_id=visit.visit_id,
        latitude=-12.0694,
        longitude=-77.0346,
        db=db_session,
    )
    assert error is None
    assert code == 200
    assert result["visit_status"] == "verified"
    assert result["dwell_minutes"] >= 20
    assert result["remaining_minutes"] == 0


def test_get_user_atlas(db_session):
    atlas = get_user_atlas("U_VISIT_TEST", db=db_session)
    assert atlas["total_verified_visits"] == 1
    assert atlas["regions_visited"] == 1
    assert len(atlas["visits"]) == 1
    stamp = atlas["visits"][0]
    assert stamp["destination_id"] == "circuito_magico"
    assert stamp["region"] == "LIMA"
    assert stamp["dwell_minutes"] >= 20


# ==========================================
# 3. Pruebas de Endpoints HTTP (FastAPI)
# ==========================================
def test_api_active_visit_endpoint(client):
    res = client.get("/api/v1/visits/active", headers=auth_header("U_VISIT_TEST"))
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    # Como la visita anterior ya fue verificada, actualmente no hay visita activa
    assert data["data"] is None


def test_api_check_in_flow(client):
    # Nuevo check-in vía API
    payload = {
        "destination_id": "circuito_magico",
        "latitude": -12.0694,
        "longitude": -77.0346,
    }
    res = client.post("/api/v1/visits/check-in", json=payload, headers=auth_header("U_VISIT_TEST"))
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["visit_status"] == "in_progress"


def test_api_atlas_endpoint(client):
    res = client.get("/api/v1/visits/atlas", headers=auth_header("U_VISIT_TEST"))
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["total_verified_visits"] >= 1
