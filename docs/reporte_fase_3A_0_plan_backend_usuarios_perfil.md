# Reporte de Planificación: Fase 3A.0 — Backend para Usuarios Reales y Perfil Viajero

## 1. Resumen Ejecutivo
Se ha realizado un análisis de la estructura actual del backend (`proxvel_backend`) para definir la hoja de ruta de la Fase 3A. El objetivo es estructurar el soporte nativo en PostgreSQL para usuarios reales, autenticación mínima y almacenamiento persistente del perfil viajero. Este paso es el prerrequisito arquitectónico para poder desconectar al frontend de su actual dependencia de mocks y del *fallback* estático `U00001`.

## 2. Estado actual del backend
- El backend fue inicializado en Fases 1 y 2 primordialmente como un servicio de catálogo (Destinos MINCETUR) y colector de opiniones (Reviews).
- Existe un router `/users` (`user_routes.py`) pero solo expone `GET /users/demo` y `GET /users/{user_id}` para lectura básica.
- El script de *seeding* inyecta usuarios estáticos (`U00001`, `U00002`, `U00003`) con una contraseña en texto plano `"demo_not_for_auth"`, cuyo único propósito ha sido dar integridad referencial (Foreign Key) a las reseñas pre-cargadas.

## 3. Limitaciones actuales
- **No hay Auth real:** FastAPI carece de endpoints `POST /register` y `POST /login`. No utiliza esquemas de tokens (JWT), y la librería `passlib` o similares no están instaladas en `requirements.txt`.
- **Perfil Viajero fantasma:** Aunque el modelo de base de datos existe, no hay esquemas Pydantic (`traveler_profile_schema.py`) ni routers (`profile_routes.py`) para gestionar las preferencias del viajero. El seeder no crea perfiles para los usuarios demo.

## 4. Tablas existentes relevantes
- `users`: Actualmente estructurada con `id`, `user_id` (string), `name`, `email`, `password_hash`, `role` e `is_active`.
- `traveler_profiles`: Estructurada con preferencias cualitativas (`presupuesto`, `clima_preferido`, `tolerancia_multitudes`) y 10 pesos cuantitativos ABSA (del 1 al 5 o del 0.0 al 1.0) para atractivos, costos, seguridad, etc.
 Ambas tablas **ya existen** en PostgreSQL según los modelos actuales y la migración `165537726253_initial_phase_2a.py`.

## 5. Propuesta de modelo de usuarios
Dado que la tabla `users` ya está correctamente modelada mediante SQLAlchemy (`app/models/user_model.py`), **se propone reutilizarla sin modificaciones estructurales mayores**. 
- `user_id`: Se mantendrá como identificador único (ej. `U00004` autogenerado o UUID, decisión a confirmar).
- `password_hash`: Se utilizará activamente pero requerirá la implementación futura de hasheo real. Para la Fase 3A inicial (MVP sin JWT), se puede guardar texto o un hash simple simulado, para luego incorporar `passlib`.

## 6. Propuesta de modelo de perfil viajero
Se **reutilizará** la tabla `traveler_profiles` existente (`app/models/traveler_profile_model.py`), ya que sus campos encajan perfectamente con los aspectos de la aplicación:
- **Cualitativos:** `budget_preference`, `climate_preference`, `crowd_preference`.
- **Cuantitativos (Pesos de 1 a 5):** `peso_accesibilidad`, `peso_aforo_multitudes`, `peso_alojamiento`, `peso_atencion_servicio`, `peso_atractivos`, `peso_clima`, `peso_costos`, `peso_gastronomia`, `peso_limpieza`, `peso_seguridad`.
La única validación necesaria será forzar a que estos valores se mantengan dentro del rango de negocio establecido.

## 7. Endpoints propuestos
Para satisfacer el MVP de la Fase 3A se proponen los siguientes endpoints (sin seguridad JWT inicial):

**User Router (`/api/v1/users`):**
- `POST /` - Registrar un usuario nuevo. El backend autogenera el `user_id` e inicializa su perfil viajero en blanco o por defecto.
- `GET /{user_id}` - Obtener información pública del usuario.
- `PATCH /{user_id}` - Actualizar nombre o contraseña.

**Profile Router (`/api/v1/profiles`):**
- `GET /user/{user_id}` - Obtener el perfil viajero completo.
- `PUT /user/{user_id}` - Reemplazar el perfil viajero por uno nuevo (Onboarding).
- `PATCH /user/{user_id}` - Actualización parcial (preferencias modificadas desde "Mi Cuenta").

*Nota: `POST /auth/login` y `POST /auth/register` con JWT quedan postergados para una subfase posterior.*

## 8. Schemas propuestos
Se creará `app/schemas/traveler_profile_schema.py` y se expandirá `user_schema.py`:
- `UserCreate` (In: name, email, password)
- `UserUpdate` (In: name, password)
- `UserResponse` (Out: info sin password_hash)
- `TravelerProfileUpdate` (In: presupuesto, clima, pesos)
- `TravelerProfileResponse` (Out: entidad completa para el frontend)

## 9. Migraciones necesarias
**No se requiere ninguna migración estructural de base de datos** (ni creación de tablas ni agregado de columnas) ya que `users` y `traveler_profiles` fueron creadas en fases anteriores. Sí podría considerarse a futuro una migración de datos para estandarizar los hashes de contraseñas de los usuarios demo.

## 10. Seeders necesarios
Se debe actualizar el script `app/scripts/seed_demo_users_reviews.py` para que, al momento de instanciar a `U00001`, `U00002` y `U00003`, también se les asigne un `TravelerProfile` con pesos mock. Esto evitará errores de 404 si el sistema intenta leer los perfiles de los usuarios de prueba.

## 11. Impacto en Flutter
Al implementar estos endpoints, la app en Flutter deberá sufrir los siguientes cambios (en Fase 3B):
- **Onboarding:** La pantalla inicial de gustos deberá hacer un `PUT /profiles/user/{user_id}` en lugar de guardar con `LocalStorageService`.
- **Registro/Login:** Dejarán de simularse localmente; consumirán `POST /users` y manejarán errores HTTP (ej. correo duplicado).
- **Adiós Fallbacks:** `MyReviewsController` y el módulo de reseñas dejarán de forzar el ID `U00001` y usarán el ID provisto por la nueva respuesta de registro.

## 12. Riesgos
- **Rotura de reseñas por FK:** Si se alteran o borran los usuarios demo (`U00001`), se perderá la cascada de la tabla `reviews` y la app de Flutter se verá vacía.
- **Usuarios sin perfil:** Si un usuario se crea por base de datos o por error en el endpoint sin que se inicialice su `TravelerProfile`, el frontend podría romper al intentar dibujar la vista "Mi Cuenta".
- **Falta de Seguridad MVP:** Construir la base sin JWT significa que momentáneamente cualquiera podría hacer un `PUT` al perfil de otro usuario adivinando el `user_id`.

## 13. Plan de implementación por subfases
Se recomienda el siguiente orden lógico y seguro:
- **Fase 3A.1:** Crear endpoints CRUD básicos de Usuario y Perfil Viajero (sin JWT).
- **Fase 3A.2:** Refactorizar el Seeder para incluir TravelerProfiles a los usuarios Demo, e inyectar validaciones Pydantic.
- **Fase 3B:** Integrar Flutter (frontend) consumiendo los endpoints de la Fase 3A.1 y 3A.2. Eliminación técnica del fallback `U00001`.
- **Fase 3C:** (Opcional/Posterior) Implementar Auth real (JWT, `passlib`) para proteger los endpoints ya conectados.

## 14. Qué NO se debe implementar todavía
- **Autenticación real (JWT/Bearer Token):** Complejizará las pruebas tempranas del frontend.
- **Cloudinary/S3 para avatares:** Las imágenes de perfil siguen fuera de scope.
- **Integración con Favoritos/Rutas:** Dejar eso para Fase 4.

## Confirmaciones de la Fase 3A.0
- [x] Confirmo que **NO se modificó código backend**.
- [x] Confirmo que **NO se tocó el frontend** en esta fase.
- [x] Confirmo que **NO se ejecutaron migraciones ni comandos Docker**.
