# Guía Técnica Completa del Backend PROXVEL

**PROXVEL Backend** es una API REST construida con **FastAPI** (Python) que sirve como núcleo lógico para el sistema de recomendación turística inteligente. Integra los resultados metodológicos de tesis (modelos de recomendación ABSA, afinidad destino-perfil, re-ranking contextual) con una infraestructura operativa transaccional para usuarios reales, incluyendo captura de feedback mediante reseñas y exportación de datos para reentrenamiento de modelos.

---

## 1. Descripción General del Backend

El backend PROXVEL implementa:
- **API REST** con FastAPI para consumo por aplicaciones móviles (Flutter) y web
- **Persistencia Dual**: PostgreSQL como capa primaria + CSV como fallback automático
- **Metodología Tesis**: Integración de 4 fases de procesamiento:
  - Fase 1: Catálogo turístico (MINCETUR)
  - Fase 2: ABSA (Análisis de Aspectos en Reseñas)
  - Fase 3: Afinidad destino-perfil
  - Fase 4: Re-ranking contextual (clima, aforo)
- **Ciclo MLOps**: Captura de reseñas → Exportación mensual → Reentrenamiento de modelos
- **Alta Disponibilidad**: Fallback automático a CSV si PostgreSQL cae (sin error HTTP 500)

---

## 2. Arquitectura por Capas

El proyecto utiliza el patrón **MVC extendido con Repository Pattern e inyección de dependencias**:

```
┌─────────────────────────────────────────────────────────┐
│  FastAPI Application (app/main.py)                       │
│  └─ CORS Configured                                      │
│  └─ Lifespan: CSV Precache on Startup                   │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
   ┌─────────────┐ ┌──────────┐ ┌────────────┐
   │   Routes    │ │Services  │ │Repositories│
   │ (Handlers)  │ │(Business)│ │ (Data I/O) │
   └─────────────┘ └──────────┘ └────────────┘
        ↓              ↓              ↓
   ┌──────────────────┼──────────────┐
   │                  ↓              ↓
   │         ┌─────────────────┐ ┌─────────┐
   │         │   Schemas       │ │ Models  │
   │         │  (Pydantic)     │ │(SQLAlch)│
   │         └─────────────────┘ └─────────┘
   │
   └──────────────┬──────────────┐
                  ↓              ↓
           ┌─────────────┐ ┌──────────┐
           │ PostgreSQL  │ │CSV Files │
           │   (Primary) │ │(Fallback)│
           └─────────────┘ └──────────┘
```

### Componentes Clave

- **`app/routes/`**: Controladores de endpoints FastAPI organizados por dominio:
  - `health_routes.py`: Verificación de salud
  - `data_routes.py`: Estado de datos y modo operativo
  - `destination_routes.py`: Catálogo de destinos
  - `recommendation_routes.py`: Ranking contextual y búsqueda
  - `tourism_routes.py`: Catálogo turístico MINCETUR
  - `user_routes.py`: Gestión de usuarios
  - `review_routes.py`: Captura de reseñas y feedback
  - `admin_training_routes.py`: Admin MLOps (exportación/entrenamiento)

- **`app/services/`**: Lógica de negocio y orquestación:
  - `destination_service.py`: Enriquecimiento y filtrado de destinos
  - `tourism_service.py`: Datos turísticos de MINCETUR
  - `recommendation_service.py`: Búsqueda y ranking base
  - `contextual_ranking_service.py`: Re-ranking con clima/aforo
  - `user_service.py`: Gestión de usuarios demo
  - `review_service.py`: Validación y persistencia de reseñas
  - `monthly_export_service.py`: Exportación de lotes para entrenamiento
  - `model_update_run_service.py`: Seguimiento de entrenamientos
  - `data_status_service.py`: Diagnóstico de estado de datos

- **`app/repositories/`**: Abstracción de datos con patrón Fallback:
  - `csv_loader.py`: Carga y caché en memoria de 5 CSV metodológicos
  - `db_*_repository.py`: Lectura desde PostgreSQL con try/except
  - `*_repository.py`: Diccionarios cacheados desde CSV
  - Sistema automático: intenta DB → si falla → retorna CSV cacheado

- **`app/schemas/`**: Modelos Pydantic para validación de requests/responses (Contratos JSON):
  - `destination_schema.py`: Estructura de destinos con scores
  - `tourism_schema.py`: Ficha turística oficial
  - `recommendation_schema.py`: Resultados de ranking
  - `user_schema.py`: Perfil de usuario
  - `review_schema.py`: Reseña con ratings por aspecto
  - `monthly_export_schema.py`: Lote de exportación
  - `model_update_run_schema.py`: Carrera de entrenamiento
  - `common_schema.py`: Respuesta estándar (success, data, message)

- **`app/models/`**: Modelos ORM de SQLAlchemy para PostgreSQL:
  - `destination_model.py`, `tourism_catalog_model.py`, `aspect_score_model.py`
  - `climate_score_model.py`, `crowd_score_model.py`, `contextual_ranking_model.py`
  - `user_model.py`, `review_model.py`, `review_aspect_rating_model.py`
  - `monthly_review_batch_model.py`, `model_update_run_model.py`

- **`app/config/`**: Configuración centralizada:
  - `settings.py`: Pydantic Settings con variables de entorno (DATABASE_URL, CORS_ORIGINS, etc.)
  - `database.py`: Engine SQLAlchemy y SessionLocal factory
  - `cors.py`: Configuración CORS (permitir orígenes)

- **`app/data/`**: 5 archivos CSV metodológicos (origen e inmutable):
  - `destinations_catalog.csv`: Catálogo de 3 destinos de Fase 1
  - `matriz_absa_normalizada.csv`: Scores de aspectos (Fase 2)
  - `aforo_scores.csv`: Scores de aforo por destino/mes (Fase 4)
  - `clima_scores.csv`: Scores de clima por destino/mes (Fase 4)
  - `ranking_contextual_final.csv`: 9000 registros de ranking final (Fase 4)

- **`app/exports/`**: Directorio para exportaciones generadas:
  - `reviews/`: Lotes mensuales de reseñas exportadas (archivos CSV)
  - Formato: `reviews_{year}_{month:02d}_batch_{batch_id}.csv`
  - Creado automáticamente en Fase 2E

- **`app/scripts/`**: Utilidades administrativas:
  - `seed_database.py`: Carga los 5 CSV a PostgreSQL (requiere DB encendida)
  - `seed_demo_users_reviews.py`: Crea 3 usuarios demo con reseñas
  - `reset_seeded_tables.py`: Limpia tablas seeded (para desarrollo)
  - `check_database_counts.py`: Audita conteos finales en DB

- **`app/utils/`**: Funciones auxiliares:
  - `response_builder.py`: Wrapper estándar de respuestas (success, data, message)
  - `normalizers.py`: Funciones de limpieza (generate_destination_id, safe_float, etc.)

---

## 3. Entorno Local (Docker y Python)

### 3.1 Requisitos Previos
- Python 3.12+
- Docker (para PostgreSQL)
- Pip o Poetry
- Git

### 3.2 Instalación de Dependencias

```bash
# Clonar/navegar al repositorio
cd proxvel_backend

# Crear y activar entorno virtual
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

**Dependencias principales** (requirements.txt):
```
fastapi              # Framework web
uvicorn[standard]    # Servidor ASGI
pydantic             # Validación de datos
pydantic-settings    # Gestión de entorno
pandas               # Manejo de CSV
python-dotenv        # Carga de .env
httpx                # Cliente HTTP (testing)
pytest               # Testing framework
sqlalchemy           # ORM y queries
psycopg2-binary      # Driver PostgreSQL
alembic              # Migraciones de BD
```

### 3.3 Configuración de Variables de Entorno

Copia `.env.example` a `.env` en la raíz y completa los valores:

```env
# Entorno de ejecución
APP_ENV=development

# Configuración de aplicación
APP_NAME=PROXVEL Backend
APP_VERSION=1.0.0
DEBUG=True
HOST=0.0.0.0
PORT=8000

# Directorio de datos CSV
DATA_DIR=app/data

# CORS - orígenes permitidos (separados por coma)
CORS_ORIGINS=*

# URL de conexión a PostgreSQL
DATABASE_URL=postgresql://proxvel_user:proxvel_password@localhost:5432/proxvel_db
```

**Nota:** La variable `DATABASE_URL` se ignora automáticamente en local si no existe el contenedor PostgreSQL.

### 3.4 Levantar PostgreSQL

El backend depende de PostgreSQL. Se recomienda usar Docker:

```bash
# Si el contenedor ya existe
docker start proxvel_postgres

# Si no existe, crear desde imagen oficial
docker run -d \
  --name proxvel_postgres \
  -e POSTGRES_USER=proxvel_user \
  -e POSTGRES_PASSWORD=proxvel_password \
  -e POSTGRES_DB=proxvel_db \
  -p 5432:5432 \
  postgres:16

# Verificar que está corriendo
docker ps | grep proxvel_postgres
```

### 3.5 Cargar Datos Iniciales en PostgreSQL

Una vez que PostgreSQL está encendido:

```bash
# Opción 1: Script seeder (carga 5 CSV + 3 usuarios demo)
.\venv\Scripts\activate
python -m app.scripts.seed_database
python -m app.scripts.seed_demo_users_reviews

# Opción 2: Usar Alembic para migraciones (si existen)
alembic upgrade head

# Verificar conteos
python -m app.scripts.check_database_counts
```

### 3.6 Ejecutar el Backend

```bash
.\venv\Scripts\activate
python run.py
```

El servidor arrancará en `http://127.0.0.1:8000`. La aplicación realiza:
1. Precarga de los 5 CSV en memoria (csv_fallback)
2. Intento de conexión a PostgreSQL (DATABASE_URL)
3. Si todo OK → modo `database` (PostgreSQL primario)
4. Si DB falla → modo `csv_fallback` (sin error HTTP 500)

### 3.7 Acceder a la Documentación API

Una vez arrancado el backend:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

Ambas muestran todos los endpoints, esquemas Pydantic y ejemplos interactivos.

### 3.8 Ejecutar Tests

La suite completa de tests cubre:
- Endpoints de salud y estado
- Destinos, catálogo turístico, recomendaciones
- Usuarios y reseñas
- Exportación mensual y entrenamientos

```bash
# Ejecutar todos los tests con salida detallada
python -m pytest -v

# Ejecutar solo un archivo
python -m pytest tests/test_health.py -v

# Ejecutar solo un test
python -m pytest tests/test_health.py::test_health_returns_200 -v

# Ejecutar con cobertura (si coverage está instalado)
python -m pytest --cov=app tests/ -v
```

**Resultado esperado**: 25 tests `PASSED` (con PostgreSQL encendido).

---

## 4. Flujos de Datos Principales

### 4.1 Flujo CSV → PostgreSQL → API

```
Startup
  ↓
+──────────────────────────────────────────┐
│ CSV Loader: Precarga 5 CSV en memoria   │
│ (diccionarios cacheados en repositorios)│
└──────────────────────────────────────────┘
  ↓
+──────────────────────────────────────────┐
│ Intenta conectar a PostgreSQL            │
│ (DATABASE_URL en settings)               │
└──────────────────────────────────────────┘
  ↓
┌─ ¿Conexión exitosa? ─────────────┐
│                                  │
SI                                NO
│                                  │
↓                                  ↓
data_mode: "database"      data_mode: "csv_fallback"
Queries SQL en DB          Retorna diccionarios CSV
(9000 rankings, etc.)      en memoria (alta velocidad)
fallback_available: true   fallback_available: true
```

**Ciclo de una petición GET** (ej. `/api/v1/destinations`):
1. Route handler llama a `destination_service.get_destinations()`
2. Service llama a `destination_repository.get_all()`
3. Repository intenta `db_destination_repository.get_all()` (Query SQL)
4. Si DB está OK → devuelve resultados con `destination.model_dump()`
5. Si DB falla (Exception) → automáticamente retorna `csv_fallback["destinations"]`
6. Response se serializa con Pydantic (respeta contrato JSON)

**Ventajas**:
- Transaccionalidad con DB cuando está disponible
- Alta disponibilidad con CSV (sin requerimientos de replicación)
- Sin código duplicado: repositories manejan la lógica de fallback
- Respuesta idéntica (misma estructura JSON) en ambos modos

### 4.2 Flujo de Reseñas (Reviews)

```
Usuario en Flutter/Web
  ↓
POST /api/v1/reviews
{
  "user_id": "U00001",
  "destination_id": "machu-picchu",
  "rating_general": 5.0,
  "review_text": "Increíble destino",
  "aspect_ratings": [
    {"aspect": "atractivos", "rating": 5.0},
    {"aspect": "accesibilidad", "rating": 3.0}
  ]
}
  ↓
review_service.create_review()
  ├─ Valida user_id existe
  ├─ Valida destination_id existe
  └─ Crea Review con estado "pending_processing"
  ↓
db_review_repository.create()
  ├─ INSERT en tabla reviews (PostgreSQL)
  ├─ INSERT en tabla review_aspect_ratings (1 registro por aspecto)
  └─ Retorna review_id generado
  ↓
Response 201 Created
{
  "success": true,
  "data": {
    "review_id": "uuid-...",
    "user_id": "U00001",
    "destination_id": "machu-picchu",
    "status": "pending_processing",
    "created_at": "2026-06-09T14:30:00Z"
  }
}
```

**Estados de una reseña**:
- `pending_processing`: Acaba de crearse, lista para exportar en lote mensual
- `exported`: Se incluyó en un lote mensual (`MonthlyReviewBatch`)
- `processed`: El sistema externo la procesó y reentrenó (se notifica vía `PATCH /admin/training-batches/{batch_id}`)
- `used_for_training`: Estado final (archivado para auditoría)

### 4.3 Flujo de Exportación Mensual (MLOps)

```
Fin de Mes / Admin ejecuta
  ↓
POST /api/v1/admin/training-batches/monthly
{
  "year": 2026,
  "month": 6,
  "format": "csv"
}
  ↓
monthly_export_service.create_monthly_export()
  ├─ Query: SELECT * FROM reviews WHERE status='pending_processing'
  ├─ Genera batch_id: "B{year}{month}{uuid_short}"
  │  Ejemplo: "B202606A1B2"
  ├─ Escribe archivo CSV en app/exports/reviews/{filename}
  │  Nombre: reviews_{year}_{month:02d}_batch_{batch_id}.csv
  │  Ejemplo: reviews_2026_06_batch_B202606A1B2.csv
  ├─ Estructura CSV:
  │  Columnas: review_id, user_id, destination_id, rating_general,
  │            review_text, visit_date, source, language,
  │            is_verified_visit, validation_method, status,
  │            processing_month, created_at, aspect_ratings_json
  │  - aspect_ratings_json: JSON serializado con aspectos
  │    Ejemplo: [{"aspect": "atractivos", "rating": 5.0, "comment": "..."}]
  ├─ UPDATE reviews SET status='exported' WHERE status='pending_processing'
  └─ INSERT MonthlyReviewBatch(batch_id, status='exported', export_path, created_at)
  ↓
Response 201
{
  "success": true,
  "data": {
    "batch_id": "B202606A1B2",
    "status": "exported",
    "export_path": "app/exports/reviews/reviews_2026_06_batch_B202606A1B2.csv",
    "review_count": 42
  }
}

[Sistema externo procesa corpus CSV con LLM/NLP]

  ↓
PATCH /api/v1/admin/training-batches/{batch_id}
{
  "new_status": "used_for_training"
}
  ↓
UPDATE reviews SET status='processed'
UPDATE monthly_review_batches SET status='used_for_training'
  ↓
INSERT model_update_run(status='completed', batch_id, timestamp)
```

**Archivos generados**:
- `app/exports/reviews/` contiene archivos CSV (uno por mes/batch)
- Nombrado: `reviews_{YYYY}_{MM}_batch_{batch_id}.csv`
- Formato: CSV con encabezado + filas de reseñas
- Columna `aspect_ratings_json`: Contiene array JSON de aspectos (serializado)
- Permite procesamiento por herramientas externas (Python, R, etc.)

---

## 5. Endpoints Principales

### 5.1 Health y Estado

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/health` | GET | Verificación simple de salud |
| `/api/v1/data/status` | GET | Estado completo: modo (database/csv_fallback), conteos BD, disponibilidad fallback |

### 5.2 Catálogo de Destinos

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/destinations` | GET | Lista todos los destinos con scores ABSA y clima |
| `/api/v1/destinations/{destination_id}` | GET | Detalle de un destino (incluye matriz ABSA, clima, aforo) |
| `/api/v1/tourism/catalog` | GET | Lista catálogo turístico oficial (MINCETUR) |
| `/api/v1/tourism/catalog/{destination_id}` | GET | Ficha turística oficial de MINCETUR |
| `/api/v1/tourism/map-markers` | GET | Coordenadas para mapa (lat, lng, nombre) |

### 5.3 Recomendaciones y Búsqueda

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/recommendations/contextual?user_id=U00001` | GET | Ranking contextual final (Fase 4) con re-ranking clima/aforo |
| `/api/v1/recommendations/search?query=machu` | GET | Búsqueda por texto en destinos |
| `/api/v1/recommendations/base` | GET | Info sobre recomendaciones base (Fase 3) |

### 5.4 Usuarios y Reseñas

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/users/demo` | GET | Lista usuarios demo (demo1, demo2, demo3) |
| `/api/v1/users/{user_id}` | GET | Datos de un usuario |
| `/api/v1/reviews` | POST | Crear nueva reseña (con ratings por aspecto) |
| `/api/v1/reviews/pending` | GET | Reseñas pendientes de exportación |
| `/api/v1/reviews/destination/{destination_id}` | GET | Reseñas para un destino |
| `/api/v1/reviews/user/{user_id}` | GET | Reseñas de un usuario |
| `/api/v1/reviews/{review_id}` | GET | Detalle de una reseña |

### 5.5 Admin / MLOps

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/admin/training-batches` | GET | Lista lotes de exportación |
| `/api/v1/admin/training-batches/monthly` | POST | Crear lote mensual (exporta pending_processing) |
| `/api/v1/admin/training-batches/{batch_id}` | PATCH | Marcar lote como `used_for_training` |
| `/api/v1/admin/model-update-runs` | GET | Lista carreras de entrenamiento |
| `/api/v1/admin/model-update-runs` | POST | Registrar nueva carrera de entrenamiento |

---

## 6. Explicación de Estados MLOps

### Estados de Reseñas

```
pending_processing  →  exported  →  processed  →  (discarded opcional)
     ↑                   ↑            ↑
  Creada en API   Incluida en      Sistema
                  lote mensual     externo
                  (CSV export)     procesó
```

**Estados posibles**:
- `pending_processing`: Reseña acaba de crearse, lista para exportar en lote mensual
- `exported`: Incluida en un lote mensual (archivo CSV generado)
- `processed`: Sistema externo la procesó y reentrenó modelos
- `discarded`: Reseña rechazada/spam (opcional, si se implementa validación)

**Transiciones**:
- `pending_processing` → `exported`: Al crear lote mensual `POST /admin/training-batches/monthly`
- `exported` → `processed`: Cuando sistema externo procesa el CSV
- `processed` → (archivada): Registrada para auditoría

### Estados de Lotes Mensuales

```
exported → used_for_training
   ↑            ↑
Reseñas     Sistema externo
exportadas  completó entrenamiento
```

**Uso en FlutterFlow**:
- Solo verificar estado en `/api/v1/reviews/pending` (sin filtrar por status)
- No exponemos estado en pantalla a usuario final
- Admin puede monitorear en dashboard interno

---

## 7. Troubleshooting

### "ConnectionRefusedError: PostgreSQL"
1. Verifica que contenedor está corriendo: `docker ps | grep proxvel_postgres`
2. Si no: `docker start proxvel_postgres`
3. Backend cambia automáticamente a `csv_fallback` sin error

### "DatabaseError: relation doesn't exist"
1. Tables no fueron creadas: `python -m app.scripts.seed_database`
2. O usar Alembic: `alembic upgrade head`

### "ModuleNotFoundError: No module named 'app'"
1. Asegúrate de estar en raíz del proyecto
2. Entorno virtual activado
3. `pip install -r requirements.txt`

### Tests fallan con "fixture error"
1. PostgreSQL debe estar encendido para `pytest`
2. Alembic/seed_database deben haber corrido
3. Limpia caché: `rm -rf .pytest_cache`

---

## 8. Próximos Pasos

Una vez que el backend está operativo:
1. **Integración Flutter**: Usar guía `docs/guia_integracion_flutter_backend.md`
2. **Autenticación**: Implementar JWT/OAuth2 si requerido
3. **Monitoreo**: Agregar Prometheus/Grafana para métricas
4. **CI/CD**: Configurar GitHub Actions o similar
5. **Performance**: Cachear endpoints con Redis si es necesario
