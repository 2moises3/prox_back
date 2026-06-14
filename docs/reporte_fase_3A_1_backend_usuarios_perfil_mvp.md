# Reporte de Cierre: Fase 3A.1 — Backend MVP de Usuarios Reales y Perfil Viajero

## 1. Resumen Ejecutivo
Se implementaron exitosamente los endpoints y la arquitectura base para dar soporte nativo a usuarios reales y a sus perfiles de viajero en la base de datos PostgreSQL, reemplazando la dependencia teórica de los usuarios demo y sentando las bases para conectar el frontend. Todo el trabajo se mantuvo dentro del `proxvel_backend`, sin afectar la app de Flutter, garantizando que el MVP sea completamente funcional sin instalar dependencias complejas (JWT/bcrypt).

## 2. Archivos Creados/Modificados
- **Modificados:**
  - `app/repositories/db_user_repository.py`: Se añadieron métodos para buscar por email, generar IDs y crear/actualizar usuarios.
  - `app/services/user_service.py`: Lógica de negocio para manejar duplicados, hashear passwords y delegar al repositorio.
  - `app/routes/user_routes.py`: Exposición de los endpoints `POST /users`, `PATCH /users/{user_id}` y todos los relacionados al `traveler-profile`.
  - `app/schemas/user_schema.py`: Ajustado para `UserCreate` y `UserUpdate`, evitando enviar el `password_hash` en las respuestas.
- **Creados:**
  - `app/utils/hash_util.py`: Utilidad MVP usando la librería nativa `hashlib.pbkdf2_hmac`.
  - `app/schemas/traveler_profile_schema.py`: Definición Pydantic de las preferencias y los pesos ABSA con validaciones de rangos (`ge=1.0, le=5.0`).
  - `app/repositories/db_traveler_profile_repository.py`: Lógica de base de datos para recuperar, reemplazar y actualizar parcialmente perfiles.
  - `app/services/traveler_profile_service.py`: Lógica para asegurar validaciones de existencia de usuario antes de operar con el perfil.

## 3. Endpoints Implementados
Los siguientes endpoints están activos y testeados:
- `POST /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `PATCH /api/v1/users/{user_id}`
- `GET /api/v1/users/{user_id}/traveler-profile`
- `PUT /api/v1/users/{user_id}/traveler-profile`
- `PATCH /api/v1/users/{user_id}/traveler-profile`

## 4. Reglas de generación de `user_id`
Al crear un usuario, el backend consulta el último `user_id` en PostgreSQL (ej. `U00003`) y autogenera el siguiente valor correlativo (ej. `U00004`), asegurando compatibilidad total con el patrón demo inicial.

## 5. Regla de hash de password
Se implementó un hash seguro de manera nativa utilizando `hashlib.pbkdf2_hmac`. Para asegurar la unicidad y resistencia de las contraseñas, se utiliza un **salt aleatorio** de 16 bytes único por cada usuario, en combinación con 100,000 iteraciones.

El valor resultante se almacena en la base de datos bajo un formato combinado estandarizado:
`pbkdf2_sha256$iterations$salt_hex$hash_hex`

No se guardan contraseñas en texto plano ni se instalan dependencias externas. Esta solución es un MVP sin JWT/login todavía, que asegura la viabilidad inmediata y previene la debilidad de un salt fijo. En la Fase 3D (Autenticación Formal), esta misma estructura y arquitectura permitirá una transición fluida hacia `passlib` o `bcrypt`. El endpoint `POST /users` tampoco expone el `password_hash` en su respuesta JSON.

### Corrección de seguridad sobre hash de contraseña
Tras una auditoría inicial, se detectó y corrigió la vulnerabilidad de usar un *salt fijo* para el MVP. Se reescribió `app/utils/hash_util.py` para invocar `os.urandom(16)` y almacenar el hash combinado, garantizando que cada usuario real creado desde Flutter tenga una huella criptográfica única, haciéndolo apto y seguro para producción temprana sin recurrir a paquetes adicionales.

## 6. Reglas de perfil viajero
- El perfil es 1 a 1 con el usuario.
- `GET` y `PATCH` devuelven 404 si el perfil no ha sido inicializado.
- `PUT` crea un perfil nuevo si no existe, o limpia/reemplaza el anterior si existe.
- Se implementaron validaciones con Pydantic (`Field(ge=1.0, le=5.0)`) asegurando que los 10 pesos cualitativos no escapen a las métricas del WSM/modelo de ranking.

## 7. Pruebas y Resultados
Se diseñó un script end-to-end automatizado (`test_mvp_3a.py`) validado directamente usando `FastAPI.TestClient`. 
- **Resultados:** `ALL TESTS PASSED`. 
- Se confirmó creación (`201`), validación de duplicados (`409`), actualización, `404` para perfiles no inicializados y éxito total en inserciones PUT y parcheos PATCH.

## 8. Confirmaciones obligatorias de la fase
- [x] NO se tocó código en el frontend (Flutter).
- [x] NO se implementó JWT ni rutas Auth formales.
- [x] NO se ejecutaron migraciones estructurales destructivas.
- [x] NO se borraron usuarios demo (`U00001`, etc.).
- [x] La compilación (`python -m compileall app`) no arrojó errores de sintaxis.

## 9. Deuda técnica restante
Para las siguientes fases, queda pendiente:
1. **Fase 3A.2:** Actualizar los *seeders* para darles un perfil viajero inicial (TravelerProfile) a los usuarios demo actuales.
2. **Fase 3B:** Integración en Flutter (Onboarding y Registro) para sustituir el LocalStorage y conectar las vistas al backend.
3. **Fase 3C:** Eliminación definitiva del fallback `U00001` en el código de Flutter una vez el paso 3B sea estable.
4. **Fase 3D:** Formalización del módulo de Autenticación (Rutas login/register, JWT y reemplazo de `hashlib` por `bcrypt`/`passlib`).

---
*Este reporte valida técnica y operacionalmente los requerimientos MVP estipulados para la Fase 3A.1.*
