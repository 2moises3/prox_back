# Reporte — Plan de Implementación Backend Fase 2 (PostgreSQL + Reviews)

> **Proyecto:** PROXVEL Backend  
> **Fecha de Análisis:** 2026-06-08  
> **Especialista:** Arquitecto Backend Senior  
> **Objetivo:** Transición progresiva de CSV a PostgreSQL, integración de esquema de reseñas y pipeline externo de actualización, manteniendo estables los endpoints de la Fase 1/1B.

---

## 1. Resumen Ejecutivo
Este documento establece el plan arquitectónico para la Fase 2 del Backend de PROXVEL. Se plantea una migración progresiva donde los CSV originales actúan como fuente semilla para popular una base de datos PostgreSQL mediante SQLAlchemy y Alembic. Además, se diseña un módulo robusto para recolectar reseñas reales de usuarios, las cuales serán almacenadas y exportadas en lotes mensuales para un proceso externo de reentrenamiento, asegurando que el backend no modifique los modelos predictivos en tiempo de ejecución.

---

## 2. Estado Actual Detectado del Backend
- **Framework:** FastAPI con arquitectura limpia (routers, services, repositories).
- **Fuente de datos actual:** Lectura en memoria (`csv_loader.py`) desde 5 archivos CSV ubicados en `app/data/`.
- **Endpoints funcionales:** `/health`, `/data/status`, `/destinations`, `/recommendations/contextual`, `/recommendations/search`, `/tourism/catalog`, `/tourism/map-markers`.
- **Fase 1 y 1B Aprobadas:** Lógica de ABSA, Aforo, Clima y Catálogo Turístico (MINCETUR) operando correctamente en memoria.
- **Estructura CSV Confirmada:** 
  - `aforo_scores.csv` (22 columnas).
  - `ranking_contextual_final.csv` (28 columnas).
  - `destinations_catalog.csv` (36 columnas).
  - `clima_scores.csv` (11 columnas).
  - `matriz_absa_normalizada.csv` (11 columnas).

---

## 3. Estado Actual de PostgreSQL Esperado
- **Contenedor Docker:** `proxvel_postgres` (PostgreSQL 16) configurado y funcional.
- **Conectividad:** Puerto `5432` expuesto en `localhost`.
- **Estructura Base:** Base de datos `proxvel_db` limpia (sin tablas ni esquemas aún).
- **Acceso:** Vía DataGrip confirmado para inspección.

---

## 4. Arquitectura Objetivo
- **Capa de Datos:** PostgreSQL como fuente primaria, gestionada vía SQLAlchemy ORM (modo *sync* para mantener simplicidad con las librerías actuales, o *async* vía `asyncpg` si se requiere máxima concurrencia).
- **Capa de Migraciones:** Alembic para el control de versiones del esquema de base de datos.
- **Capa de Semilla (Seeding):** Un script orquestado que lee los CSV mediante `pandas`, limpia datos y realiza un *upsert* en PostgreSQL, permitiendo una transición suave.
- **Capa de Lógica:** `Repositories` modificados para priorizar la lectura desde PostgreSQL con un *fallback* a CSV en caso de desconexión.

---

## 5. Diseño Propuesto de Base de Datos
El esquema transaccional (OLTP) mantendrá las estructuras derivadas de la tesis, optimizando las búsquedas. Se dividirá lógicamente en dominios: Catálogo/Destinos, Scores (ABSA, Aforo, Clima), Ranking Precalculado, y Feedback (Reviews y Exportación).

---

## 6. Tablas Propuestas

1. **`destinations`**: Centraliza los destinos. (`id`, `destination_id`, `destination`, `created_at`, `updated_at`).
2. **`tourism_catalog`**: Catálogo oficial MINCETUR. (`id`, `destination_id`, `official_name`, `city`, `region`, `category`, `latitude`, `longitude`, `cover_image_url`, `gallery_image_1..4`, etc.).
3. **`destination_aspect_scores`**: Resultados ABSA por destino. (`id`, `destination_id`, `accesibilidad`, `clima`, `costos`, etc.).
4. **`climate_scores`**: Contexto climático histórico. (`id`, `destination_id`, `month`, `temp_prom`, `pp`, `clima_categoria`, `score_clima`).
5. **`crowd_scores`**: Contexto de aforo extraído del CSV real. (`id`, `destination_id`, `year`, `month`, `visitantes_mes`, `aforo_normalizado`, `nivel_aforo`, `score_aforo_base`, `periodo`).
6. **`contextual_rankings`**: Resultados finales Fase 4 precalculados. (`id`, `user_id`, `destination_id`, `rank`, `score_final_fase4`, `compatibilidad_final`, `etiqueta_final`, `explicacion_final`).
7. **`users`**: Base para registro y autenticación. (`id`, `user_id`, `name`, `email`, `password_hash`, `role`, `is_active`).
8. **`traveler_profiles`**: Preferencias estáticas del viajero. (`id`, `user_id`, `presupuesto`, `clima_preferido`, `tolerancia_multitudes`, pesos ABSA).
9. **`favorites`**: Destinos guardados. (`id`, `user_id`, `destination_id`).
10. **`reviews`**: Reseñas libres enviadas por el usuario. (`id`, `review_id`, `user_id`, `destination_id`, `rating_general`, `review_text`, `status`, `processing_month`, `training_batch_id`). Estados: `pending_processing`, `exported`, `processed`, `discarded`.
11. **`review_aspect_ratings`**: Ratings desagregados. (`id`, `review_id`, `aspect`, `rating`, `comment`).
12. **`monthly_review_batches`**: Lotes para exportación de MLOps. (`id`, `batch_id`, `year`, `month`, `total_reviews`, `status`, `export_path`). Estados: `created`, `exported`, `used_for_training`, `closed`.
13. **`model_update_runs`**: Historial de procesos de entrenamiento externo. (`id`, `run_id`, `batch_id`, `model_name`, `metrics_json`, `status`).
14. **`visits`**: Validación de presencia. (`id`, `visit_id`, `user_id`, `destination_id`, `visit_status`, `validation_method`).

---

## 7. Relaciones Propuestas
- `destinations` **1 → 1** `tourism_catalog`
- `destinations` **1 → 1** `destination_aspect_scores`
- `destinations` **1 → N** `climate_scores`
- `destinations` **1 → N** `crowd_scores`
- `destinations` **1 → N** `contextual_rankings`
- `users` **1 → N** `traveler_profiles` (Normalmente 1 a 1 activo, N por historial).
- `users` **1 → N** `favorites`
- `users` **1 → N** `reviews`
- `destinations` **1 → N** `reviews`
- `reviews` **1 → N** `review_aspect_ratings`
- `monthly_review_batches` **1 → N** `reviews`
- `monthly_review_batches` **1 → N** `model_update_runs`
- `users` **1 → N** `visits` y `destinations` **1 → N** `visits`

> **Justificación:** Se mantiene `destinations` como núcleo central, garantizando integridad referencial. El modelo permite separar el análisis estadístico precalculado (scores, rankings) de la operativa de usuario (reviews, visitas).

---

## 8. Flujo CSV → PostgreSQL
1. **Limpieza y Estructuración:** El script `seed_database.py` leerá los 5 CSVs usando `pandas` y el módulo actual `normalizers.py`.
2. **Carga Segura (Upsert):** Se procesarán los registros con mecanismos `ON CONFLICT DO UPDATE` (o borrado transaccional controlado) para asegurar idempotencia. La carga puede ejecutarse repetidas veces sin duplicar la información.
3. **Respaldo:** Los archivos CSV se mantienen en `app/data/` como copia maestra inviolable.

---

## 9. Flujo Reviews → Export Mensual → Actualización Corpus
1. **Recolección:** App móvil hace POST de reseña al backend.
2. **Almacenamiento Local:** Se inserta en PostgreSQL con estado `pending_processing`.
3. **Exportación Mensual:** Script/Endpoint extrae todas las reseñas pendientes del mes en un archivo (e.g. JSON o CSV export) y crea un registro en `monthly_review_batches`. El estado cambia a `exported`.
4. **Pipeline Externo:** El científico de datos corre modelos (ABSA, BERT, WSM) externamente, evaluando el lote exportado.
5. **Cierre de Ciclo:** Un endpoint admin permite actualizar el estado del batch a `used_for_training` o registrar una nueva versión del modelo en `model_update_runs`.

---

## 10. Subfases Recomendadas
- **Fase 2A:** Configuración de SQLAlchemy, Alembic y Modelos base. Generación de primera migración.
- **Fase 2B:** Creación de script Seeder y carga inicial desde CSV hacia PostgreSQL.
- **Fase 2C:** Actualización de Repositorios actuales para leer desde la DB, manteniendo los contratos de JSON exactos.
- **Fase 2D:** Creación del módulo de Usuarios, Favorites y Reseñas (Modelos y Endpoints).
- **Fase 2E:** Módulo de exportación mensual de Reviews (Batches) y Endpoints Admin.
- **Fase 2F:** Documentación técnica, validación manual con DataGrip, validación de endpoints y smoke tests.

---

## 11. Archivos a Crear/Modificar

**Configuración:**
- `app/config/database.py` (Engine, SessionLocal)
- `app/config/db_settings.py` o actualización de `settings.py`

**Modelos (Nuevos):**
- `app/models/base.py`
- `app/models/destination_model.py`
- `app/models/tourism_catalog_model.py`
- `app/models/aspect_score_model.py`
- `app/models/climate_score_model.py`
- `app/models/crowd_score_model.py`
- `app/models/contextual_ranking_model.py`
- `app/models/user_model.py`
- `app/models/traveler_profile_model.py`
- `app/models/favorite_model.py`
- `app/models/review_model.py`
- `app/models/review_aspect_rating_model.py`
- `app/models/monthly_review_batch_model.py`
- `app/models/model_update_run_model.py`
- `app/models/visit_model.py`

**Repositorios (Modificados/Nuevos):**
- `app/repositories/db_destination_repository.py`
- `app/repositories/db_ranking_repository.py`
- `app/repositories/db_tourism_repository.py`
- `app/repositories/db_review_repository.py`

**Servicios (Nuevos):**
- `app/services/review_service.py`
- `app/services/monthly_export_service.py`

**Rutas (Nuevas):**
- `app/routes/review_routes.py`
- `app/routes/admin_training_routes.py`

**Esquemas (Nuevos):**
- `app/schemas/review_schema.py`
- `app/schemas/monthly_export_schema.py`

**Scripts y Alembic (Nuevos):**
- `app/scripts/seed_database.py`
- `app/scripts/reset_database.py`
- `app/scripts/export_monthly_reviews.py`
- `alembic.ini`, `alembic/env.py`, `alembic/versions/`

---

## 12. Librerías Necesarias
Añadir a `requirements.txt`:
- `sqlalchemy` (ORM robusto)
- `alembic` (Migraciones)
- `psycopg2-binary` (Driver sync para PostgreSQL - recomendado para simplificar integración inicial con lógica existente) o `asyncpg` si se migra todo a async.

---

## 13. Estrategia SQLAlchemy / Alembic
- Usaremos **SQLAlchemy 2.0+** (sintaxis declarativa moderna).
- **Modo Sync:** Dado que el cargador de CSV y las rutas actuales son sincrónicas (`def` vs `async def`), se usará `psycopg2` y una sesión sincrónica inicial, facilitando la transición y evitando refactorización masiva en Fase 2.
- **Alembic:** Generación automática de migraciones `--autogenerate` basadas en los metadatos de los modelos, con revisiones atómicas.

---

## 14. Estrategia de Seeding
- El script de carga se ejecutará de forma aislada vía CLI (ej. `python -m app.scripts.seed_database`).
- Seguirá un orden estricto de inserción: Destinos → Catálogo → ABSA → Clima → Aforo → Usuarios (Dummy) → Rankings.
- Limpieza previa opcional o lógica de *Upsert* basándose en `destination_id`.

---

## 15. Estrategia de Fallback CSV
Para garantizar cero tiempo de inactividad, los Repositorios intentarán conectar a PostgreSQL (vía `Session`). Si falla (e.g. Error de conexión) o si las tablas están vacías, recurrirán al caché de memoria del `csv_loader.py` que ya está implementado. El endpoint `/data/status` se modificará para reportar si opera en modo "Database" o "CSV Fallback".

---

## 16. Endpoints Que Se Mantienen
- `GET /api/v1/health`
- `GET /api/v1/destinations` (y `/{id}`)
- `GET /api/v1/recommendations/contextual`
- `GET /api/v1/recommendations/search`
- `GET /api/v1/tourism/catalog` (y `/{id}`)
- `GET /api/v1/tourism/map-markers`
- `GET /api/v1/data/status` (Actualizado con conteos de BD y modo).

*(Nota: Los contratos JSON de salida serán rigurosamente idénticos para no quebrar la app móvil Flutter).*

---

## 17. Endpoints Nuevos Propuestos

**Reviews (Usuario App):**
- `POST /api/v1/reviews`
- `GET /api/v1/reviews/destination/{destination_id}`
- `GET /api/v1/reviews/user/{user_id}`
- `GET /api/v1/reviews/{review_id}`

**Admin / MLOps (Operador):**
- `GET /api/v1/reviews/export/monthly?year=YYYY&month=MM`
- `POST /api/v1/admin/training-batches/monthly`
- `PATCH /api/v1/admin/training-batches/{batch_id}/mark-exported`
- `PATCH /api/v1/admin/training-batches/{batch_id}/mark-used-for-training`

---

## 18. Riesgos Detectados
1. **Discrepancia de Tipos:** Los CSV pueden contener nulos o tipos mixtos (`NaN`, strings vacíos). *Mitigación: Utilizar los `normalizers.py` existentes en el seeder.*
2. **Caída del Backend:** Si PostgreSQL no levanta, los endpoints podrían fallar. *Mitigación: Implementar el Fallback a memoria.*
3. **Refactor de Sync/Async:** Mezclar sesiones asincrónicas en un ecosistema sincrónico puede generar *Deadlocks*. *Mitigación: Mantener SQLAlchemy en modo Sync inicialmente.*
4. **Sobrescritura Accidental:** El seeder podría borrar datos insertados por usuarios (e.g., Favorites/Reviews). *Mitigación: El seeder solo actualizará tablas catálogo/scores.*

---

## 19. Recomendaciones
1. Ejecutar las subfases en orden estricto, certificando la **Fase 2C** (transparencia de repositorios) antes de agregar la lógica de reviews (**Fase 2D**).
2. NO incluir JWT/Autenticación compleja en Fase 2; usar IDs estáticos de usuario temporalmente, postergando la seguridad estricta para Fase 3.
3. Agregar variables al `.env.example` enmascaradas (`DATABASE_URL=postgresql://user:pass@localhost:5432/proxvel_db`).

---

## 20. Criterios de Aceptación Futuros
- PostgreSQL conecta correctamente sin errores.
- Alembic crea las 14 tablas propuestas sin fallos.
- El Seeder puebla las tablas núcleo leyendo los 5 CSV.
- Todos los endpoints Fase 1/1B siguen operando sin alteraciones en su JSON de salida.
- `/api/v1/data/status` refleja el estado híbrido (DB + CSV).
- Es posible registrar una reseña mediante POST y recuperarla.
- Las reseñas nacen en estado `pending_processing`.
- Existe un mecanismo de exportación y empaquetamiento mensual (Batch).
- **NO existe entrenamiento de IA en runtime dentro del backend.**
- DataGrip permite verificar la correcta distribución de datos.
- Los tests `pytest` actuales (Health, Data, Catalog) pasan al 100%.

---

## 21. Qué NO Se Debe Implementar Aún
- **NO** implementar código fuente ahora.
- **NO** modificar archivos de Python.
- **NO** ejecutar `alembic upgrade head`.
- **NO** cargar los CSV en la base de datos real.
- **NO** alterar los endpoints funcionales actuales.
- **NO** integrar JWT o contraseñas reales cifradas hasta la Fase de Auth.

---
*Fin del Plan de Implementación - En espera de aprobación para inicio de Fase 2A.*
