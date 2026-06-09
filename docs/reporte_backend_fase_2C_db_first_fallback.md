# Reporte Backend Fase 2C — DB-First con Fallback CSV

**Fecha:** 2026-06-09
**Estado:** ✅ Completado exitosamente

---

## 1. Objetivo de la Fase
Actualizar la capa de repositorios para que el sistema consulte primero PostgreSQL y, en caso de fallo de conexión o tablas vacías, recurra automáticamente a los datos en memoria provenientes de los CSV. Esta transición transparente asegura alta disponibilidad sin alterar los contratos JSON hacia el frontend.

---

## 2. Archivos Creados y Modificados

**Creados:**
- `app/repositories/db_destination_repository.py`: Repositorio DB-first para destinos y scores.
- `app/repositories/db_tourism_repository.py`: Repositorio DB-first para catálogo turístico.
- `app/repositories/db_ranking_repository.py`: Repositorio DB-first para rankings contextuales.

**Modificados:**
- `app/services/destination_service.py`: Importa `db_destination_repository`.
- `app/services/tourism_service.py`: Importa `db_tourism_repository`.
- `app/services/recommendation_service.py`: Importa `db_ranking_repository`.
- `app/services/contextual_ranking_service.py`: Importa `db_ranking_repository`.
- `app/services/data_status_service.py`: Actualizado para verificar la conexión a DB, contar tablas en PostgreSQL, y emitir el estado combinado.
- `app/routes/data_routes.py`: Actualizado el docstring/descripción de `/api/v1/data/status`.
- `tests/test_health.py`: Adaptado el test `test_data_status_returns_200` al nuevo contrato JSON dinámico del status.

*(Nota: Los repositorios originales basados en CSV se mantuvieron intactos como respaldo).*

---

## 3. Estrategia DB-First y CSV Fallback
Cada función en los nuevos `db_*_repository` sigue el patrón:
1. Crea una sesión (`SessionLocal`).
2. Verifica si la tabla maestra tiene datos (ej: `db.query(Destination).count() == 0`).
3. Si la tabla está vacía o si ocurre **cualquier excepción** (timeout, DB apagada, tabla no existe):
   - Se captura la excepción en un bloque `try/except`.
   - Se emite un `logger.error/info` notificando el evento.
   - Se devuelve el resultado de llamar a la misma función en el repositorio CSV original (`fallback_repo`).
4. Si la DB está arriba y tiene datos, retorna la data mapeada al diccionario exacto que esperaba el service.

---

## 4. Contratos JSON Preservados
Los objetos retornados por PostgreSQL fueron mapeados uno a uno para coincidir con la nomenclatura del CSV:
- `type_` en DB se devuelve como `type`.
- Se reconstruyeron las listas (ej. `gallery_images` a partir de `gallery_image_1..4`).
- Se mantuvieron inmutables todos los endpoints.

---

## 5. Endpoints Validados
- `GET /api/v1/health`
- `GET /api/v1/data/status`
- `GET /api/v1/destinations`
- `GET /api/v1/destinations/{id}`
- `GET /api/v1/recommendations/contextual`
- `GET /api/v1/recommendations/search`
- `GET /api/v1/recommendations/base`
- `GET /api/v1/tourism/catalog`
- `GET /api/v1/tourism/catalog/{id}`
- `GET /api/v1/tourism/map-markers`

---

## 6. Resultado de `/api/v1/data/status`
Con la base de datos **encendida**, retorna:
```json
{
  "success": true,
  "data": {
    "data_mode": "database",
    "csv_status": {
      "loaded": true,
      "files_loaded": 5
    },
    "database_status": {
      "connected": true,
      "tables_available": true,
      "counts": {
        "destinations": 3,
        "tourism_catalog": 3,
        "destination_aspect_scores": 3,
        "climate_scores": 36,
        "crowd_scores": 766,
        "contextual_rankings": 9000
      }
    },
    "fallback_available": true
  }
}
```
Con la base de datos **apagada** (Docker Stop), retorna:
```json
{
  "success": true,
  "data": {
    "data_mode": "csv_fallback",
    "csv_status": { "loaded": true, "files_loaded": 5 },
    "database_status": { "connected": false },
    "fallback_available": true
  }
}
```

---

## 7. Pruebas de Resiliencia
- **Con PostgreSQL encendido (`docker start proxvel_postgres`):**
  - `pytest -v` pasó limpiamente en ~3 segundos (`14 passed`).
  - Los endpoints contestaron correctamente desde la DB.
- **Con PostgreSQL apagado (`docker stop proxvel_postgres`):**
  - `pytest -v` siguió pasando limpiamente (`14 passed`), tomando un poco más de tiempo (~50s) debido a los timeouts de TCP intentando contactar PostgreSQL en el `try/except` antes de activar el fallback. Esto demuestra que la alta disponibilidad está asegurada frente a caídas críticas de infraestructura.

---

## 8. Riesgos o Advertencias
- **Latencia de Timeout:** Cuando PostgreSQL está apagado, cada consulta inicial intentará conectarse a `localhost:5432`. El timeout por defecto de conexión de TCP puede añadir latencia a las peticiones (usualmente de 1 a 2 segundos por endpoint). En un entorno de producción estricto, esto se mitigaría configurando un tiempo de espera (`connect_timeout`) en el `DATABASE_URL` (ej. `?connect_timeout=2`). Para esta fase, la resiliencia base está comprobada.
- **Consultas N+1:** En endpoints como `/recommendations/search` o `/contextual` se resolvió la deduplicación y el enriquecimiento de manera manual y en memoria para coincidir 1:1 con el modelo antiguo. En el futuro, esto podría refactorizarse utilizando consultas con JOIN robustos de SQL directamente para mejor rendimiento.

---

## 9. Qué queda para Fase 2D
En la **Fase 2D**, procederemos a:
1. **Creación de Reseñas:** Implementar los endpoints `POST` para que los usuarios (con identificadores genéricos por ahora) puedan enviar reseñas.
2. **Tablas Operativas:** Empezar a escribir datos en `reviews` y `review_aspect_ratings` en PostgreSQL.
3. **Flujo Cíclico:** Establecer la infraestructura base para que estas reseñas cambien de estado (`pending_processing`).
