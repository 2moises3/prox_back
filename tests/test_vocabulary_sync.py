"""
Los intereses que ofrece la app móvil deben ser exactamente los que entiende el motor.

Un interés de la app fuera del vocabulario nunca suma coincidencias con un destino;
un interés del vocabulario que la app no ofrece no se puede elegir jamás.
Si el código de la app no está disponible (p. ej. dentro del contenedor del backend)
la prueba se omite.
"""
import re
import unicodedata
from pathlib import Path

import pytest

from app.services.recommendation_engine_v1 import INTEREST_VOCAB, _CLIMATE_PREFS, _perfil_tolerancia

APP_FILE = Path(__file__).resolve().parents[2] / "proxvel_app" / "lib" / "core" / "constants" / "traveler_vocabulary.dart"


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", text.strip().lower())
    return "".join(c for c in t if not unicodedata.combining(c))


@pytest.fixture(scope="module")
def dart_source() -> str:
    if not APP_FILE.exists():
        pytest.skip("No se encuentra proxvel_app (prueba pensada para correr en el repo completo).")
    return APP_FILE.read_text(encoding="utf-8")


def _block(src: str, name: str) -> str:
    start = src.index(name)
    return src[start:src.index("];", start)]


def test_intereses_de_la_app_son_los_del_motor(dart_source):
    app_interests = {_norm(m) for m in re.findall(r"InterestOption\('([^']+)'", _block(dart_source, "static const List<InterestOption> interests"))}
    assert app_interests == INTEREST_VOCAB, (
        f"Solo en la app: {sorted(app_interests - INTEREST_VOCAB)} | Solo en el motor: {sorted(INTEREST_VOCAB - app_interests)}"
    )


def test_climas_de_la_app_son_los_del_motor(dart_source):
    app_climates = {_norm(m) for m in re.findall(r"'([^']+)'", _block(dart_source, "static const List<String> climates"))}
    assert app_climates == _CLIMATE_PREFS


def test_tolerancias_de_la_app_se_interpretan_bien():
    # Lo que la app puede guardar (incluidos valores antiguos) debe mapear a baja/media/alta.
    casos = {"baja": "baja", "bajo": "baja", "Media": "media", "medio": "media", "moderado": "media", "alta": "alta", "Alto": "alta"}
    for valor, esperado in casos.items():
        assert _perfil_tolerancia({"tolerancia_multitudes": valor}) == esperado
