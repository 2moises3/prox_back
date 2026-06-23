"""
PROXVEL Backend - Normalizers.
Funciones de limpieza y normalización de datos provenientes de CSV.
Adaptado a las columnas reales de los CSV de tesis.
"""

import math
import re
from typing import Any


def normalize_value(value: Any) -> Any:
    """
    Normaliza un valor individual:
    - NaN/inf → None
    - Strings vacíos → None
    - Strings numéricos → float
    """
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "" or stripped.lower() in ("nan", "none", "null"):
            return None
        return stripped
    return value


def normalize_row(row: dict) -> dict:
    """Normaliza todos los valores de un diccionario (fila de CSV)."""
    return {k: normalize_value(v) for k, v in row.items()}


def safe_float(value: Any, default: float | None = None) -> float | None:
    """Convierte un valor a float de forma segura. Devuelve default si falla."""
    if value is None:
        return default
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int | None = None) -> int | None:
    """Convierte un valor a int de forma segura."""
    if value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def generate_destination_id(destination_name: str) -> str:
    """
    Genera un ID slug a partir del nombre del destino.
    Ejemplo: 'Machu Picchu' → 'machu-picchu'
    """
    if not destination_name:
        return "unknown"
    slug = destination_name.lower().strip()
    # Reemplazar caracteres especiales comunes en español
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        "ñ": "n", "ü": "u",
    }
    for orig, repl in replacements.items():
        slug = slug.replace(orig, repl)
    # Solo letras, números y espacios → guiones
    slug = re.sub(r"[^a-z0-9\s]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug or "unknown"


def clean_column_name(col: str) -> str:
    """Limpia nombres de columna: elimina BOM, espacios, etc."""
    return col.strip().lstrip("\ufeff").strip()


# Palabras vac\u00edas que no aportan identidad a un destino.
_STOP_WORDS = {
    "de", "del", "la", "las", "los", "el", "y", "e", "a", "en",
    "con", "por", "para", "al", "sin", "o", "u", "un", "una",
    "historico", "historica", "nacional", "sitio",
}


def destination_word_set(name: str) -> frozenset[str]:
    """
    Tokeniza y normaliza un nombre de destino para comparaci\u00f3n de similitud.
    Devuelve el conjunto de palabras significativas (sin stop words, sin acentos).
    """
    if not name:
        return frozenset()
    s = name.lower().strip()
    for orig, repl in [("\u00e1","a"),("\u00e9","e"),("\u00ed","i"),("\u00f3","o"),("\u00fa","u"),("\u00f1","n"),("\u00fc","u")]:
        s = s.replace(orig, repl)
    words = re.sub(r"[^a-z0-9\s]", " ", s).split()
    return frozenset(w for w in words if w not in _STOP_WORDS and len(w) > 2)


def jaccard_similarity(a: frozenset, b: frozenset) -> float:
    """Similitud Jaccard entre dos conjuntos de palabras."""
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0
