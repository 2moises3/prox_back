"""
PROXVEL Backend - CSV Loader.
Carga genérica de archivos CSV a listas de diccionarios.
Los datos se cargan una sola vez al startup y se cachean en memoria.

Columnas reales detectadas en los CSV de tesis (Fase4_V2):

matriz_absa_normalizada.csv:
  destination, accesibilidad, aforo_multitudes, alojamiento,
  atencion_servicio, atractivos, clima, costos, gastronomia,
  limpieza, seguridad

clima_scores.csv (V2):
  destination, station, month, month_name, pp, tmax, tmin,
  temp_prom, score_temperatura, score_precipitacion,
  score_clima_base, nivel_clima, riesgo_climatico,
  score_clima_modelo, nivel_clima_modelo

aforo_scores.csv (V2):
  destination, year, month, month_name, visitantes_mes,
  registros_fuente, fecha, max_visitantes_destino,
  aforo_normalizado, score_aforo_base, nivel_aforo,
  visitantes_pred_3m, aforo_pred_normalizado, score_aforo_predicho,
  nivel_aforo_predicho, aforo_modelo_normalizado,
  score_aforo_modelo, nivel_aforo_modelo

ranking_contextual_final.csv (ranking_contextual_app.csv V2):
  user_id, nueva_posicion, posicion_fase3, cambio_posicion,
  interpretacion_cambio, destination, compatibilidad_contextual_pct,
  score_final_fase4, score_fase3, score_clima_modelo,
  nivel_clima_modelo, preferencia_climatica, afinidad_climatica_usuario,
  score_aforo_modelo, nivel_aforo_modelo, M_metacontexto,
  B_contextual, P_contextual, razon_contextual_principal,
  explicacion_final, es_recomendado

destinations_catalog.csv (Fase 1B - catálogo complementario):
  destination_id, destination, official_name, department, province,
  district, city, region, category, type, subtype, hierarchy,
  altitude_m, description, experience_type, latitude, longitude,
  cover_image_url, gallery_image_1..4, image_source,
  official_source_name, official_source_code, official_source_url
"""

import logging
from pathlib import Path
from typing import Any

import pandas as pd

from app.utils.normalizers import clean_column_name, normalize_value

logger = logging.getLogger(__name__)

# ── Almacén en memoria ──────────────────────────────────────────────
# Clave → lista de dicts normalizados
_DATA_STORE: dict[str, list[dict[str, Any]] | None] = {}

# Nombres de los CSV esperados
CSV_FILES = {
    "absa": "matriz_absa_normalizada.csv",
    "clima": "clima_scores.csv",
    "aforo": "aforo_scores.csv",
    "ranking": "ranking_contextual_final.csv",
    "catalog": "destinations_catalog.csv",
}


def load_csv(filepath: Path) -> list[dict[str, Any]] | None:
    """
    Carga un archivo CSV y devuelve una lista de diccionarios.
    - Usa encoding utf-8-sig para manejar BOM de Windows.
    - Normaliza nombres de columnas.
    - Convierte NaN a None.
    Retorna None si el archivo no existe o hay error.
    """
    if not filepath.exists():
        logger.warning("CSV no encontrado: %s", filepath)
        return None

    try:
        df = pd.read_csv(filepath, encoding="utf-8-sig")
        # Limpiar nombres de columnas
        df.columns = [clean_column_name(c) for c in df.columns]

        # Convertir a lista de dicts y normalizar valores
        records = df.to_dict(orient="records")
        normalized = []
        for row in records:
            normalized.append({k: normalize_value(v) for k, v in row.items()})

        logger.info(
            "CSV cargado: %s (%d filas, columnas: %s)",
            filepath.name,
            len(normalized),
            list(df.columns),
        )
        return normalized

    except Exception as e:
        logger.error("Error al cargar CSV %s: %s", filepath.name, str(e))
        return None


def load_all_csvs(data_dir: Path) -> None:
    """
    Carga todos los CSV esperados al DATA_STORE.
    Debe llamarse una sola vez al startup de la aplicación.
    """
    global _DATA_STORE

    logger.info("Cargando CSV desde: %s", data_dir)

    for key, filename in CSV_FILES.items():
        filepath = data_dir / filename
        _DATA_STORE[key] = load_csv(filepath)

    loaded = sum(1 for v in _DATA_STORE.values() if v is not None)
    total = len(CSV_FILES)
    logger.info("CSV cargados: %d/%d", loaded, total)


def get_data(key: str) -> list[dict[str, Any]] | None:
    """
    Obtiene los datos cacheados de un CSV por su clave.
    Claves válidas: 'absa', 'clima', 'aforo', 'ranking', 'catalog'.
    """
    return _DATA_STORE.get(key)


def is_loaded(key: str) -> bool:
    """Verifica si un CSV fue cargado exitosamente."""
    return _DATA_STORE.get(key) is not None


def get_all_status() -> dict[str, bool]:
    """Devuelve el estado de carga de cada CSV."""
    return {
        CSV_FILES[key]: is_loaded(key)
        for key in CSV_FILES
    }
