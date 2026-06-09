# PROXVEL Backend

API REST para el sistema de recomendación turística personalizada **PROXVEL**.

Este backend consume las salidas CSV generadas por las fases metodológicas de la tesis y las expone mediante endpoints REST para que el frontend Flutter pueda consumirlas. Incluye un catálogo turístico oficial complementario (MINCETUR).

## Estado Actual: Backend Fase 1B ✅

- ✅ Arquitectura FastAPI por capas
- ✅ Lectura de CSV reales de tesis (4 archivos)
- ✅ Catálogo turístico oficial complementario (Fase 1B)
- ✅ 10 endpoints REST funcionales
- ✅ Swagger/OpenAPI en `/docs`
- ✅ Enriquecimiento de destinos y recomendaciones con datos MINCETUR
- ❌ PostgreSQL (fase futura)
- ❌ JWT/Auth (fase futura)
- ❌ Conexión con Flutter (fase futura)
- ❌ Visitas / feedback (fase futura)

## Tecnologías

- **Python 3.11+**
- **FastAPI** — Framework web asíncrono
- **Pydantic** — Validación y serialización
- **Pandas** — Lectura de CSV
- **Uvicorn** — Servidor ASGI

## Instalación

### 1. Crear entorno virtual

```powershell
cd proxvel_backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copiar `.env.example` a `.env` y ajustar si es necesario:

```powershell
Copy-Item .env.example .env
```

### 4. Verificar CSV

Los archivos CSV deben estar en `app/data/`:

| Archivo | Origen | Descripción |
|---------|--------|-------------|
| `matriz_absa_normalizada.csv` | Fase 2 (tesis) | Puntajes ABSA por aspecto y destino |
| `clima_scores.csv` | Fase 4 (tesis) | Scores climáticos por mes y destino |
| `aforo_scores.csv` | Fase 4 (tesis) | Scores de aforo/concurrencia |
| `ranking_contextual_final.csv` | Fase 4 (tesis) | Ranking contextual final con explicación |
| `destinations_catalog.csv` | Fase 1B (complementario) | Catálogo turístico oficial MINCETUR |

### 5. Ejecutar el backend

```powershell
python run.py
```

El servidor arranca en `http://localhost:8000`.

## Swagger UI

- **Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Endpoints Disponibles

### Endpoints base (Fase 1)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/health` | Estado del servicio |
| GET | `/api/v1/data/status` | Estado de carga de CSV |
| GET | `/api/v1/destinations` | Listar destinos (enriquecido) |
| GET | `/api/v1/destinations/{id}` | Detalle de un destino (enriquecido) |
| GET | `/api/v1/recommendations/contextual` | Ranking contextual (enriquecido) |
| GET | `/api/v1/recommendations/search` | Búsqueda por texto (enriquecido) |
| GET | `/api/v1/recommendations/base` | Stub de Fase 3 |

### Endpoints de catálogo turístico (Fase 1B)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/tourism/catalog` | Catálogo turístico oficial completo |
| GET | `/api/v1/tourism/catalog/{id}` | Detalle turístico de un destino |
| GET | `/api/v1/tourism/map-markers` | Marcadores de mapa (coordenadas válidas) |

> **Nota:** El catálogo turístico es información complementaria de fuentes oficiales (MINCETUR).
> **No afecta** los scores de recomendación, el ranking, ni la compatibilidad calculados por la tesis.

### Parámetros de Query

**`/destinations`**: `city`, `limit`

**`/recommendations/contextual`**: `user_id`, `city`, `limit`

**`/recommendations/search`**: `query`, `city`, `limit`

## Arquitectura

```
Routes → Schemas → Services → Repositories → CSV Data
```

```
proxvel_backend/
├── app/
│   ├── main.py              # App FastAPI + lifespan
│   ├── config/              # Settings, CORS
│   ├── routes/              # Endpoints HTTP (+ tourism_routes.py)
│   ├── schemas/             # Modelos Pydantic (+ tourism_schema.py)
│   ├── services/            # Lógica de negocio (+ tourism_service.py)
│   ├── repositories/        # Acceso a datos CSV (+ tourism_repository.py)
│   ├── data/                # CSV de tesis + catálogo turístico
│   └── utils/               # Response builder, normalizers
├── tests/                   # Tests con pytest (14 tests)
├── docs/                    # Reportes de fase
├── requirements.txt
├── .env / .env.example
└── run.py                   # Entry point
```

## Tests

```powershell
pytest -v
```

## Fases Futuras

- **Fase 2**: PostgreSQL + SQLAlchemy + Alembic
- **Fase 3**: JWT / Autenticación
- **Fase 4**: Integración con Flutter
- **Fase 5**: Docker + despliegue
- **Fase futura**: Visitas, feedback, mapa real
