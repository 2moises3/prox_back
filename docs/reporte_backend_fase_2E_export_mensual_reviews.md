# Reporte Backend Fase 2E — Exportación Mensual de Reseñas

**Fecha:** 2026-06-09
**Estado:** ✅ Completado exitosamente

---

## 1. Objetivo de la Fase
Implementar un "Mecanismo de retroalimentación y actualización periódica del corpus". Este módulo se encarga de empaquetar las reseñas recolectadas con estado `pending_processing`, agruparlas mensualmente, exportarlas en un formato estructurado (CSV), y cambiar su estado para simular un proceso de actualización externa en el modelo de Machine Learning, todo **sin ejecutar ningún entrenamiento ni notebook en el entorno backend**.

---

## 2. Archivos Creados y Modificados

**Creados:**
- `app/schemas/monthly_export_schema.py`: Pydantic models para el request y response de la exportación de lotes (Batches).
- `app/schemas/model_update_run_schema.py`: Pydantic models para registrar una ejecución externa del modelo.
- `app/repositories/db_monthly_batch_repository.py`: Repositorio para transacciones de lotes de entrenamiento (CRUD sobre `monthly_review_batches`).
- `app/repositories/db_model_update_run_repository.py`: Repositorio para transacciones del registro de ejecuciones externas (`model_update_runs`).
- `app/services/monthly_export_service.py`: Lógica principal para generar el CSV, consultar DB, agrupar las reseñas y actualizar los estados.
- `app/services/model_update_run_service.py`: Servicio para insertar ejecuciones de modelos.
- `app/routes/admin_training_routes.py`: El router con los endpoints admin expuestos.
- `tests/test_training_batches.py`: Pruebas de integración sobre los nuevos endpoints admin.
- Directorio de exportación garantizado: `app/exports/reviews/`.

**Modificados:**
- `app/repositories/db_review_repository.py`: Se añadió la función `get_and_mark_reviews_for_export()` para atar atómicamente la obtención de reseñas y su marcado a estado `exported`.
- `app/main.py`: Se incorporó el nuevo router `admin_training_routes`.

---

## 3. Endpoints Nuevos Habilitados
Bajo el prefijo `/api/v1/admin`:
- `POST /training-batches/monthly`: Inicia el escaneo y crea el CSV.
- `GET /training-batches`: Lista todos los batches generados.
- `GET /training-batches/{batch_id}`: Detalle de un batch exportado.
- `PATCH /training-batches/{batch_id}/mark-used-for-training`: Avanza el batch y sus reviews al estado `used_for_training` / `processed`.
- `POST /model-update-runs`: Simula e ingresa al historial de base de datos un reentrenamiento finalizado en sistemas externos.
- `GET /model-update-runs`: Muestra el historial de ejecuciones externas del ML.

---

## 4. Flujo de Exportación Mensual y Estados
1. El cliente ejecuta el `POST` para exportar el mes (ej: `2026-06`).
2. El sistema recupera todas las reseñas con estado `pending_processing`.
3. Crea un registro en `monthly_review_batches`.
4. Genera el CSV.
5. Pasa el estado de las reseñas a `exported` asociándoles el `training_batch_id`.
6. Al finalizar el análisis externo, se utiliza el `PATCH /mark-used-for-training`. El batch cambia a `used_for_training` y todas sus reseñas hijas pasan a `processed`.
7. Opcionalmente se crea un registro de trazabilidad en `model_update_runs`.

---

## 5. Formato del CSV Generado
El archivo se genera bajo la estructura:
```csv
review_id,user_id,destination_id,rating_general,review_text,visit_date,source,language,is_verified_visit,validation_method,status,processing_month,created_at,aspect_ratings_json
rev-xxx,U00001,machu-picchu,5.0,El lugar...,2026-06-09,app,es,False,self_report_pending,exported,2026-06,2026-06-09T...,"[{"aspect": "atractivos", "rating": 5.0, "comment": "Genial"}]"
```
Los aspect ratings se serializan limpiamente en JSON permitiendo a un script en Python/Pandas cargarlo como diccionarios usando `json.loads()`.

---

## 6. Ruta del Archivo Exportado
Al crearse un lote para `2026-06`, el path devuelto y guardado es:
`app/exports/reviews/reviews_2026_06_batch_B202606XXXX.csv`

---

## 7. Conteos Antes y Después de Ejecutar
**Antes de Phase 2E:**
- `users`: 3
- `reviews`: 6 (estado: `pending_processing`)
- `monthly_review_batches`: 0
- `model_update_runs`: 0

**Después de probar Fase 2E:**
- `users`: 3
- `reviews`: 6 (estado: `processed` tras marcar usado)
- `monthly_review_batches`: 1 (estado: `used_for_training`)
- `model_update_runs`: 1 (registrado simuladamente)

---

## 8. Resultados de Pruebas
- **`pytest -v`**: `4 passed` en la suite de admin_training_routes, cubriendo la creación, obtención, el error 404 (simulado), y el bloqueo de registros inválidos.
- **`python run.py`**: El servidor Uvicorn levanta correctamente los routers y el módulo MLOps es completamente visible en Swagger.

---

## 9. Confirmaciones de Restricciones
Cumpliendo rígidamente con los lineamientos:
- **NO** se entrenó ningún modelo de Inteligencia Artificial internamente.
- **NO** se llamaron ni se modificaron notebooks de validación en tiempo de ejecución.
- **NO** se implementó Cloudinary, ni fotos.
- **NO** se instaló JWT, login ni validaciones de auth. Todo corre sin tokens.

---

## 10. Qué queda para siguientes iteraciones
Con Fase 2E completada, el Backend cuenta con bases de datos transaccionales, fallbacks a CSV pre-cacheados y tuberías de simulación de MLOps. Los siguientes pasos estratégicos podrían involucrar Auth JWT, la conexión directa al Front-end en Flutter o el inicio de una migración del ecosistema MLOps puro.
