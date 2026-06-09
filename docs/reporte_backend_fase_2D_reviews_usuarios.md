# Reporte Backend Fase 2D — Usuarios y Reseñas Demo

**Fecha:** 2026-06-09
**Estado:** ✅ Completado exitosamente

---

## 1. Objetivo de la Fase
Implementar la infraestructura base para registrar y leer usuarios básicos y reseñas en PostgreSQL. Esto habilita que la aplicación PROXVEL guarde calificaciones reales de aspectos turísticos sin afectar el flujo de la Fase 1 o 2C, sirviendo de base para la próxima actualización periódica del modelo.

---

## 2. Archivos Creados y Modificados

**Creados:**
- `app/schemas/user_schema.py`: Pydantic models para el usuario.
- `app/schemas/review_schema.py`: Pydantic models para reseñas y ratings por aspecto.
- `app/repositories/db_user_repository.py`: Repositorio de DB para usuarios.
- `app/repositories/db_review_repository.py`: Repositorio de DB para reseñas y ratings.
- `app/services/user_service.py`: Lógica de servicio para usuarios.
- `app/services/review_service.py`: Lógica de validación para reseñas (destino válido, usuario válido, aspectos válidos).
- `app/routes/user_routes.py`: Endpoints para usuarios bajo `/api/v1/users`.
- `app/routes/review_routes.py`: Endpoints para reseñas bajo `/api/v1/reviews`.
- `app/scripts/seed_demo_users_reviews.py`: Script para inyectar datos de prueba.
- `tests/test_reviews.py`: Suite de tests automatizados para validar los nuevos endpoints.
- `alembic/versions/f3c559b1fe02_add_review_extra_fields.py`: Migración de Alembic para asegurar todos los campos (visit_date, source, language, is_verified_visit, validation_method) en la tabla `reviews`.

**Modificados:**
- `app/main.py`: Se registraron los nuevos enrutadores `user_routes` y `review_routes`.
- `app/models/review_model.py`: Se añadieron los campos extras solicitados antes de migrar.

---

## 3. Usuarios Demo Creados
Se crearon 3 usuarios en la tabla `users` mediante el script seeder:
- `U00001` (Usuario Demo 1, demo1@proxvel.local)
- `U00002` (Usuario Demo 2, demo2@proxvel.local)
- `U00003` (Usuario Demo 3, demo3@proxvel.local)

*(Nota: Tienen `password_hash = "demo_not_for_auth"`, sin mecanismos de autenticación ni JWT).*

---

## 4. Reseñas Demo y Aspect Ratings Creados
Se registraron 6 reseñas en total (todas con estado `pending_processing` y `processing_month = 2026-06`):
- **Machu Picchu:** 2 reseñas (U00001, U00002) - 8 aspect ratings en total.
- **Lago Titicaca:** 2 reseñas (U00001, U00003) - 8 aspect ratings en total.
- **Circuito Mágico del Agua:** 2 reseñas (U00002, U00003) - 8 aspect ratings en total.

---

## 5. Endpoints Nuevos Habilitados
- `GET /api/v1/users/demo`: Lista los usuarios de prueba.
- `GET /api/v1/users/{user_id}`: Devuelve el perfil de usuario.
- `POST /api/v1/reviews`: Crea una nueva reseña y sus aspect ratings.
- `GET /api/v1/reviews/{review_id}`: Obtiene una reseña en específico con sus aspectos.
- `GET /api/v1/reviews/destination/{destination_id}`: Historial de reseñas de un lugar.
- `GET /api/v1/reviews/user/{user_id}`: Historial de reseñas de un viajero.
- `GET /api/v1/reviews/pending`: Reseñas pendientes de procesamiento para el ML.

---

## 6. Validaciones Implementadas
El `POST /api/v1/reviews` implementa estrictamente las siguientes reglas:
1. `user_id` debe existir en DB (Error 404).
2. `destination_id` debe existir en DB (Error 404).
3. `rating_general` de 1 a 5 (Error 422 - Pydantic Field).
4. `review_text` con `min_length=1` (Error 422 - Pydantic Field).
5. Aspectos válidos (atractivos, costos, etc.) (Error 422 - Service Validator).
6. Rating por aspecto de 1 a 5 (Error 422 - Pydantic Field).

---

## 7. Conteos Finales en PostgreSQL
Tras ejecutar el Seeder, la DB arroja:
- **`users`**: 3
- **`reviews`**: 6
- **`review_aspect_ratings`**: 24

---

## 8. Resultados de Pruebas
- **`pytest -v`**: `7 passed` en `test_reviews.py` (Validando éxito, usuarios inexistentes y destinos inexistentes). Los 14 tests previos (`test_health.py`) continúan exitosos sin regresiones.
- **`python run.py`**: El backend Uvicorn inicia sin problemas, cargando tanto la DB como los CSV como fallback, y mostrando los nuevos endpoints en `/docs`.

---

## 9. Confirmaciones de Seguridad / Alcance
De acuerdo a las restricciones de la Fase 2D:
- **NO** se implementó JWT ni roles reales de auth.
- **NO** se implementó Cloudinary ni fotos de perfil o de reseña.
- **NO** se implementó export mensual ni se entrena el modelo en runtime. El estado se limita a `pending_processing`.

---

## 10. Qué queda para Fase 2E
En la **Fase 2E** iniciaremos la arquitectura de la ingesta o "Exportación Mensual" y la simulación del reentrenamiento asíncrono, integrando la estructura necesaria para que el modelo de ML pueda ingerir estos nuevos datos periódicamente.
