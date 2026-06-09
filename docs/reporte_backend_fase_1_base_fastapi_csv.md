# Reporte Backend Fase 1 — Base FastAPI + CSV

**Fecha:** 2026-06-08
**Estado:** ✅ Completado exitosamente

---

## 1. Objetivo de la Fase

Crear la arquitectura base del backend PROXVEL con FastAPI, capaz de:
- Ejecutarse localmente con Uvicorn
- Cargar los 4 archivos CSV reales de tesis al startup
- Exponer 7 endpoints REST funcionales
- Devolver respuestas JSON limpias y tipadas vía Swagger/OpenAPI

---

## 2. Archivos Creados (35 archivos)

### Estructura Final

```
proxvel_backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── cors.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health_routes.py
│   │   ├── destination_routes.py
│   │   ├── recommendation_routes.py
│   │   └── data_routes.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common_schema.py
│   │   ├── destination_schema.py
│   │   └── recommendation_schema.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── destination_service.py
│   │   ├── recommendation_service.py
│   │   ├── contextual_ranking_service.py
│   │   └── data_status_service.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── csv_loader.py
│   │   ├── destination_repository.py
│   │   └── ranking_repository.py
│   ├── data/
│   │   ├── matriz_absa_normalizada.csv
│   │   ├── clima_scores.csv
│   │   ├── aforo_scores.csv
│   │   └── ranking_contextual_final.csv
│   └── utils/
│       ├── __init__.py
│       ├── response_builder.py
│       └── normalizers.py
├── tests/
│   ├── __init__.py
│   └── test_health.py
├── docs/
│   ├── .gitkeep
│   └── reporte_backend_fase_1_base_fastapi_csv.md
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── README.md
└── run.py
```

---

## 3. Columnas Detectadas en Cada CSV

### matriz_absa_normalizada.csv (3 filas)
| Columna | Tipo | Ejemplo |
|---------|------|---------|
| destination | str | "Machu Picchu" |
| accesibilidad | float | 0.5007 |
| aforo_multitudes | float | 0.4717 |
| alojamiento | float | 0.7130 |
| atencion_servicio | float | 0.6737 |
| atractivos | float | 0.6197 |
| clima | float | 0.6416 |
| costos | float | 0.5393 |
| gastronomia | float | 0.7480 |
| limpieza | float | 0.4805 |
| seguridad | float | 0.5089 |

### clima_scores.csv (36 filas)
| Columna | Tipo | Ejemplo |
|---------|------|---------|
| destination | str | "Machu Picchu" |
| station_selected | str | "CAMPO DE MARTE" |
| station | str | "CAMPO DE MARTE" |
| month | int | 1 |
| month_name | str | "Enero" |
| tmax | float | 25.6 |
| tmin | float | 20.4 |
| pp | float | 0.6 |
| temp_prom | float | 23.0 |
| clima_categoria | str | "Favorable" |
| score_clima | float | 1.0 |

### aforo_scores.csv (766 filas)
| Columna | Tipo | Ejemplo |
|---------|------|---------|
| destination | str | "Circuito Mágico del Agua" |
| year | int | 2007 |
| month | int | 7 |
| visitantes_mes | float | 52250.0 |
| registros_mes | int | 1 |
| aforo_normalizado | float | 0.1168 |
| nivel_aforo | str | "Bajo" |
| score_aforo_base | float | 0.8831 |
| + 14 columnas adicionales de predicción | — | — |

### ranking_contextual_final.csv (9000 filas, 3000 usuarios × 3 destinos)
| Columna | Tipo | Ejemplo |
|---------|------|---------|
| user_id | str | "U00001" |
| destination | str | "Lago Titicaca" |
| rank | int | 1 |
| score_fase3 | float | 0.6409 |
| score_wsm | float | 0.6409 |
| score_cosine_referencia | float | 0.8478 |
| modelo_usado | str | "WSM - suma ponderada" |
| compatibilidad | float | 64.1 |
| etiqueta_triclase | str | "Parcialmente recomendado" |
| clima_preferido | str | "templado" |
| tolerancia_multitudes | str | "baja" |
| score_clima | float | 0.0 |
| score_aforo | float | 1.0 |
| score_final_fase4 | float | 0.5986 |
| rank_fase4 | int | 1 |
| compatibilidad_final | float | 59.87 |
| etiqueta_final | str | "Parcialmente recomendado" |
| explicacion_final | str | "El destino obtiene un score final de 59.87%..." |

---

## 4. Mapeos Aplicados

| Dato | Columna CSV Real | Campo API |
|------|-----------------|-----------|
| ID destino | (generado como slug) | `destination_id` |
| Nombre | `destination` | `destination` |
| Ciudad | No existe en CSV | `city` → `null` |
| Categoría | No existe en CSV | `category` → `null` |
| Score final | `score_final_fase4` | `final_score` |
| Compatibilidad | `compatibilidad_final` | `compatibility_percentage` |
| Etiqueta | `etiqueta_final` | `label` |
| Explicación | `explicacion_final` | `short_explanation` |
| Score clima | `score_clima` | `context.weather_score` |
| Score aforo | `score_aforo` | `context.crowd_score` |
| Categoría clima | `clima_categoria` | `context.weather_category` |
| Nivel aforo | `nivel_aforo` | `context.crowd_level` |

**Nota:** Los CSV tienen BOM UTF-8 (`\ufeff`). Se maneja con `encoding="utf-8-sig"` en pandas + `clean_column_name()` como fallback.

---

## 5. Endpoints Implementados

| # | Endpoint | Estado | Descripción |
|---|----------|--------|-------------|
| 1 | `GET /api/v1/health` | ✅ Funcional | Estado del servicio |
| 2 | `GET /api/v1/data/status` | ✅ Funcional | Estado de carga de CSV |
| 3 | `GET /api/v1/destinations` | ✅ Funcional | Lista 3 destinos |
| 4 | `GET /api/v1/destinations/{id}` | ✅ Funcional | Detalle con ABSA + contexto |
| 5 | `GET /api/v1/recommendations/contextual` | ✅ Funcional | Ranking Fase 4 |
| 6 | `GET /api/v1/recommendations/search` | ✅ Funcional | Búsqueda por texto |
| 7 | `GET /api/v1/recommendations/base` | ⏳ Stub | Fase 3 parcial |

---

## 6. Ejemplos de Respuesta

### GET /api/v1/health
```json
{"status": "ok", "service": "PROXVEL Backend", "version": "1.0.0"}
```

### GET /api/v1/data/status
```json
{
  "matriz_absa_normalizada.csv": true,
  "clima_scores.csv": true,
  "aforo_scores.csv": true,
  "ranking_contextual_final.csv": true
}
```

### GET /api/v1/destinations/machu-picchu
```json
{
  "success": true,
  "message": "Detalle de destino obtenido correctamente",
  "data": {
    "destination_id": "machu-picchu",
    "destination": "Machu Picchu",
    "city": null,
    "category": null,
    "aspect_scores": {
      "accesibilidad": 0.5007,
      "aforo_multitudes": 0.4717,
      "alojamiento": 0.7130,
      "atencion_servicio": 0.6737,
      "atractivos": 0.6197,
      "clima": 0.6416,
      "costos": 0.5393,
      "gastronomia": 0.7480,
      "limpieza": 0.4805,
      "seguridad": 0.5089
    },
    "context": {
      "weather_score": 0.0,
      "crowd_score": 0.4840,
      "weather_category": "Desfavorable",
      "crowd_level": "Medio"
    }
  }
}
```

### GET /api/v1/recommendations/contextual?user_id=U00001
```json
{
  "success": true,
  "message": "Ranking contextual obtenido correctamente",
  "data": [
    {
      "rank": 1,
      "destination_id": "lago-titicaca",
      "destination": "Lago Titicaca",
      "compatibility_percentage": 59.87,
      "label": "Parcialmente recomendado",
      "final_score": 0.5986,
      "short_explanation": "El destino obtiene un score final de 59.87%...",
      "context": {
        "weather_score": 0.0,
        "crowd_score": 1.0,
        "weather_category": "Desfavorable",
        "crowd_level": "Bajo"
      }
    }
  ],
  "count": 3
}
```

---

## 7. CSV Cargados Correctamente

```
CSV cargado: matriz_absa_normalizada.csv (3 filas, 11 columnas)
CSV cargado: clima_scores.csv (36 filas, 11 columnas)
CSV cargado: aforo_scores.csv (766 filas, 22 columnas)
CSV cargado: ranking_contextual_final.csv (9000 filas, 28 columnas)
CSV cargados: 4/4
```

---

## 8. Confirmaciones de Alcance

| Restricción | Cumplida |
|-------------|----------|
| No se implementó PostgreSQL | ✅ |
| No se implementó SQLAlchemy | ✅ |
| No se implementó Alembic | ✅ |
| No se implementó JWT | ✅ |
| No se implementó login/register real | ✅ |
| No se implementaron modelos ORM | ✅ |
| No se implementó Docker | ✅ |
| No hay IA real en runtime | ✅ |
| No se conectó con Flutter | ✅ |
| No se usan servicios cloud | ✅ |

---

## 9. Resultado de Ejecución

### python run.py
```
✅ Servidor inicia correctamente en http://0.0.0.0:8000
✅ Swagger disponible en http://localhost:8000/docs
✅ 4/4 CSV cargados al startup
✅ 7/7 endpoints respondiendo HTTP 200
```

### pytest -v
```
✅ 8/8 tests PASSED en 1.49s
- test_health_returns_200 PASSED
- test_data_status_returns_200 PASSED
- test_destinations_returns_200 PASSED
- test_contextual_ranking_returns_200 PASSED
- test_search_returns_200 PASSED
- test_base_recommendations_returns_200 PASSED
- test_destination_detail_not_found PASSED
- test_destination_detail_machu_picchu PASSED
```

---

## 10. Errores Pendientes / Observaciones

| # | Observación | Severidad | Notas |
|---|------------|-----------|-------|
| 1 | `city` y `category` devuelven `null` | Baja | Los CSV no contienen estas columnas. Se llenarán en fase futura |
| 2 | `/recommendations/base` es stub | Esperado | No existe CSV independiente de Fase 3 |
| 3 | Encoding de caracteres especiales | Info | Los CSV usan UTF-8 con BOM; se maneja con `utf-8-sig`. En consola Windows los caracteres como "ó", "á" pueden mostrarse como `�` pero internamente son correctos |
| 4 | `aspect_scores` es `null` en ranking contextual | Baja | El CSV de ranking no incluye scores ABSA; se podría enriquecer cruzando con ABSA en fase futura |

---

## 11. Recomendaciones para Backend Fase 2

1. **PostgreSQL**: Migrar datos de CSV a tablas PostgreSQL con SQLAlchemy + Alembic. Solo reescribir repositories.
2. **JWT/Auth**: Implementar autenticación con `python-jose` o `PyJWT`. Agregar dependency injection de `current_user`.
3. **Enriquecer datos**: Agregar columnas `city` y `category` a los CSV o a las tablas PostgreSQL.
4. **Cross-enrich**: Cruzar scores ABSA con ranking contextual para que `/recommendations/contextual` devuelva `aspect_scores` completos.
5. **Docker**: Crear `Dockerfile` y `docker-compose.yml` para despliegue reproducible.
6. **Conexión Flutter**: Configurar CORS con origins específicos del emulador/dispositivo Flutter.
7. **Tests**: Expandir test suite con casos edge y tests de integración.
8. **Logging**: Agregar logging estructurado (JSON) para producción.
