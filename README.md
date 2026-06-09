# PROXVEL Backend

API REST para el sistema de recomendación turística personalizada **PROXVEL**.

Este backend consume las salidas CSV generadas por las fases metodológicas de la tesis (modelos de NLP, ranking y afinidad) y las expone mediante endpoints REST para que el frontend Flutter las consuma. Integra una arquitectura de base de datos transaccional con un sistema de fallback automático, asegurando alta disponibilidad.

---

## 🚀 Estado Actual: Backend Fase 2F ✅ (Cierre Técnico Completado)

El backend se encuentra totalmente implementado y listo para integración con el cliente móvil, contando con las siguientes características:

- ✅ Arquitectura **FastAPI** por capas (MVC extendido)
- ✅ Persistencia en **PostgreSQL** + **SQLAlchemy** (ORM) + **Alembic** (Migraciones)
- ✅ Resiliencia con **Fallback automático a CSV** (Sin error 500 ante caídas de DB)
- ✅ Catálogo turístico oficial complementario integrado (Fase 1B)
- ✅ Captura de **Feedback de Usuarios** (Reseñas con procesamiento NLP ABSA)
- ✅ Módulo **MLOps simulado** (Exportación de lotes mensuales para reentrenamiento)
- ✅ Suite de Pruebas Automatizadas (**pytest**) 100% Passed
- ✅ Interfaz **Swagger/OpenAPI** interactiva en `/docs`
- ❌ **JWT/Auth real** (fase futura opcional)
- ❌ **Integración total con Flutter** (fase inminente)

---

## 🛠 Tecnologías

- **Python 3.12+**
- **FastAPI** — Framework web asíncrono
- **PostgreSQL** — Motor de Base de Datos principal
- **SQLAlchemy & Alembic** — ORM y control de versiones de BD
- **Pydantic v2** — Validación y serialización
- **Pandas** — Lectura y manipulación de CSV
- **Uvicorn** — Servidor ASGI
- **Pytest** — Pruebas unitarias y de integración

---

## ⚙️ Instalación y Despliegue Local

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

Asegúrate de configurar `DATABASE_URL` apuntando a una instancia válida de PostgreSQL.

### 4. Base de Datos y Datos Semilla

1. **Levantar PostgreSQL:** Puedes usar Docker si prefieres:
   ```bash
   docker run -d --name proxvel_postgres -e POSTGRES_USER=usuario -e POSTGRES_PASSWORD=password -e POSTGRES_DB=proxvel_db -p 5432:5432 postgres:16
   ```
2. **Aplicar migraciones:**
   ```bash
   alembic upgrade head
   ```
3. **Poblar datos (Seed):** (Opcional, carga los CSV en la base de datos)
   ```bash
   python -m app.scripts.seed_database
   python -m app.scripts.seed_demo_users_reviews
   ```

### 5. Ejecutar el backend

```powershell
python run.py
```

El servidor arrancará en `http://localhost:8000`.

---

## 📚 Documentación Interactiva (Swagger UI)

- **Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🔌 Endpoints Principales

### Sistema y Salud
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/health` | Estado de salud general de la API |
| GET | `/api/v1/data/status` | Modo operativo (`database` vs `csv_fallback`) y métricas |

### Turismo y Catálogo
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/destinations` | Listado de destinos metodológicos con scores (ABSA) |
| GET | `/api/v1/destinations/{id}` | Detalle profundo de destino, clima y aforo |
| GET | `/api/v1/tourism/catalog` | Fichas turísticas oficiales (MINCETUR) |

### Recomendaciones Inteligentes
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/recommendations/contextual` | Ranking final personalizado (`user_id`) |
| GET | `/api/v1/recommendations/search` | Búsqueda por texto enriquecida |

### Usuarios y Reseñas (Feedback Loop)
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/reviews` | Registrar reseñas y ratings por aspectos (1-5) |
| GET | `/api/v1/users/demo` | Listar usuarios demo del sistema |

### MLOps Admin (Exportación Mensual)
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/admin/training-batches/monthly` | Agrupa reseñas pendientes en lotes y exporta a CSV para reentrenamiento |
| GET | `/api/v1/admin/training-batches` | Historial de lotes procesados |

*(Los parámetros query como `?user_id=U00001` y `?limit=10` están documentados en `/docs`).*

---

## 🏗 Arquitectura del Sistema

La arquitectura está diseñada para alta tolerancia a fallos, utilizando un patrón dual donde toda petición a Base de Datos cuenta con un rescate silencioso hacia un caché CSV.

```
Routes ↔ Schemas ↔ Services ↔ Repositories ↔ [ PostgreSQL (Primary) ]
                                             ↘ [ CSV Cache (Fallback) ]
```

### Estructura del Código

```text
proxvel_backend/
├── app/
│   ├── main.py              # Entry point FastAPI + Configuración CORS + Lifespan
│   ├── config/              # Gestión de variables .env y conexión de Base de datos
│   ├── routes/              # Controladores de tráfico HTTP
│   ├── services/            # Lógica central del negocio y reglas operativas
│   ├── repositories/        # Conexión DB First / DB Fallback a memoria CSV
│   ├── schemas/             # Pydantic (Validación de entradas y salidas)
│   ├── models/              # Modelos SQLAlchemy para la BD Relacional
│   ├── data/                # CSV Semilla de Minería de Datos (Inmutables)
│   ├── exports/             # Output de MLOps simulado
│   ├── scripts/             # Utilitarios (Seeders, Checks, Resets)
│   └── utils/               # Wrappers y Normalizadores estándar
├── tests/                   # Pruebas automatizadas (pytest)
├── alembic/                 # Migraciones de esquema
├── docs/                    # Documentación y reportes de fases
└── run.py                   # Lanzador oficial Uvicorn
```

---

## 🧪 Pruebas Automatizadas

La suite actual garantiza el correcto funcionamiento del modelo de fallbacks y validaciones 404/422.
```powershell
pytest -v
```

---

## 📂 Archivos y Carpetas Ignoradas (.gitignore)
Se asegura que los siguientes elementos **NO** sean subidos al repositorio:
- `venv/` y `.venv/` (Entornos virtuales)
- `__pycache__/` y compilados `*.pyc`
- `.env` (Credenciales y configuraciones locales)
- **`cocoasas` / `cocoasas/`** (Archivos temporales o privados especificados por directiva)
- `.pytest_cache/` y `.coverage`

---

## 🔮 Fases Futuras

- **Fase 3**: Integración completa con cliente móvil **Flutter**.
- **Fase 4**: Autenticación segura (**JWT / OAuth2**) y Control de Accesos (RBAC).
- **Fase 5**: Integración de pasarela de MLOps real y actualización de pesos del modelo.
- **Fase 6**: Contenerización total (Docker Compose multi-node) y CI/CD.
