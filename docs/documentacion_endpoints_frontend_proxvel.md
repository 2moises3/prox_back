# Documentación de Endpoints para Frontend PROXVEL

## 1. Objetivo del documento

Este documento tiene como objetivo principal servir como guía técnica para alinear el desarrollo del frontend (Flutter) con los datos y estructuras reales que actualmente entrega el backend (FastAPI). Detalla los endpoints disponibles, los contratos de datos (JSON), y clarifica qué información está lista para consumirse y qué características quedan para futuras iteraciones, permitiendo una correcta evaluación del diseño actual de la UI frente a la realidad del sistema.

## 2. URL base

Dependiendo del entorno desde el cual el frontend consuma la API, la URL base será:

*   **Local PC / navegador web:** `http://127.0.0.1:8000/api/v1`
*   **Emulador Android:** `http://10.0.2.2:8000/api/v1`
*   **Dispositivo físico (misma red WiFi):** `http://IP_LOCAL_DE_LA_PC:8000/api/v1`

## 3. Resumen general de endpoints

| Módulo | Método | Endpoint | Uso en frontend | Pantalla sugerida |
|---|---|---|---|---|
| **Health** | GET | `/health` | Verificar si el backend está activo | Splash Screen / Debug |
| **Data** | GET | `/data/status` | Verificar estado de conexión DB/CSV | Settings / Admin / Debug |
| **Destinations** | GET | `/destinations` | Listar todos los destinos disponibles | Búsqueda / Explorar |
| **Destinations** | GET | `/destinations/{id}` | Ver detalle completo con scores ABSA | Detalle de Destino |
| **Recommendations** | GET | `/recommendations/contextual` | Mostrar recomendaciones personalizadas | Home / Para ti |
| **Recommendations** | GET | `/recommendations/search` | Buscar destinos por texto | Búsqueda |
| **Recommendations** | GET | `/recommendations/base` | Info sobre Fase 3 (Actualmente stub) | N/A |
| **Tourism** | GET | `/tourism/catalog` | Listar catálogo oficial MINCETUR | Catálogo / Listado |
| **Tourism** | GET | `/tourism/catalog/{id}` | Ficha oficial de MINCETUR | Detalle (Sección Info Oficial) |
| **Tourism** | GET | `/tourism/map-markers` | Puntos para mostrar en Google Maps | Mapa interactivo |
| **Users** | GET | `/users/demo` | Listar usuarios de prueba | Pantalla de Login Demo |
| **Users** | GET | `/users/{user_id}` | Obtener perfil del usuario actual | Perfil |
| **Reviews** | POST | `/reviews` | Enviar una nueva calificación y comentario | Calificar Destino / Feedback |
| **Reviews** | GET | `/reviews/destination/{id}` | Ver reseñas de un destino | Detalle de Destino (Reseñas) |
| **Reviews** | GET | `/reviews/user/{id}` | Ver historial de reseñas del usuario | Perfil / Mis Reseñas |
| **Reviews** | GET | `/reviews/{id}` | Ver detalle de una reseña específica | Detalle de Reseña |
| **Reviews** | GET | `/reviews/pending` | Listar reseñas pendientes de procesar | Panel Admin (Futuro) |
| **Admin** | POST | `/admin/training-batches/monthly` | Crear lote mensual (exportación) | Mantenimiento / CLI |
| **Admin** | GET | `/admin/training-batches` | Listar lotes de exportación | Mantenimiento / CLI |
| **Admin** | GET | `/admin/training-batches/{id}` | Detalle de un lote | Mantenimiento / CLI |
| **Admin** | PATCH | `/admin/training-batches/{id}/mark-used...` | Marcar lote como procesado | Mantenimiento / CLI |
| **Admin** | POST | `/admin/model-update-runs` | Registrar ejecución de modelo externo | Mantenimiento / CLI |
| **Admin** | GET | `/admin/model-update-runs` | Listar ejecuciones del modelo | Mantenimiento / CLI |

> **Nota sobre Endpoints Admin:** Los endpoints bajo `/admin/` **no son para pantallas públicas del usuario final**. Son para administración, propósito de tesis y mantenimiento del ciclo de actualización externa de modelos.

---

## 4. Detalle por endpoint

### Health Check
*   **Nombre:** Estado del servicio
*   **Método:** `GET`
*   **URL:** `/api/v1/health`
*   **Parámetros:** Ninguno.
*   **Campos importantes para Flutter:** `status` (debe ser "ok").
*   **Observaciones:** Útil para verificar conectividad antes de hacer peticiones pesadas.

### Estado de Datos
*   **Nombre:** Estado de carga de CSV y Base de Datos
*   **Método:** `GET`
*   **URL:** `/api/v1/data/status`
*   **Parámetros:** Ninguno.
*   **Campos importantes para Flutter:** `data.database_status.connected` (bool).
*   **Observaciones:** Sirve para saber si la API está leyendo de PostgreSQL o de los CSV de respaldo.

### Lista de Destinos
*   **Nombre:** Listar destinos
*   **Método:** `GET`
*   **URL:** `/api/v1/destinations`
*   **Parámetros:** `city` (string, opcional), `limit` (int, opcional, por defecto 50).
*   **Campos importantes para Flutter:** `destination_id`, `destination`, `cover_image_url`, `city`.
*   **Pantalla:** Lista general de destinos, Explorar.

### Detalle de Destino
*   **Nombre:** Detalle de destino
*   **Método:** `GET`
*   **URL:** `/api/v1/destinations/{destination_id}`
*   **Parámetros:** `destination_id` (en el path, ej: `machu-picchu`).
*   **Campos importantes para Flutter:** `aspect_scores` (todos los floats), `context.crowd_level`, `context.weather_category`, `tourism_info` (galería, descripción).
*   **Pantalla:** Pantalla principal de detalle del destino.

### Recomendaciones Contextuales
*   **Nombre:** Ranking contextual final
*   **Método:** `GET`
*   **URL:** `/api/v1/recommendations/contextual`
*   **Parámetros:** `user_id` (string, opcional, por defecto usa el primero disponible como demo), `city` (string, opcional), `limit` (int, opcional, por defecto 10).
*   **Campos importantes para Flutter:** `rank`, `compatibility_percentage` (para barras de progreso), `label` (para tags UI), `destination`, `cover_image_url`.
*   **Pantalla:** Home / Sección "Para Ti".

### Búsqueda de Destinos
*   **Nombre:** Búsqueda
*   **Método:** `GET`
*   **URL:** `/api/v1/recommendations/search`
*   **Parámetros:** `query` (string, opcional, texto a buscar), `city` (string, opcional), `limit` (int, opcional, por defecto 10).
*   **Campos importantes para Flutter:** `destination_id`, `destination`, `compatibility_percentage`.
*   **Pantalla:** Pantalla de búsqueda global.

### Catálogo Turístico
*   **Nombre:** Catálogo oficial
*   **Método:** `GET`
*   **URL:** `/api/v1/tourism/catalog`
*   **Parámetros:** Ninguno.
*   **Campos importantes para Flutter:** `official_name`, `category`, `type`.
*   **Pantalla:** Explorador de catálogo MINCETUR.

### Marcadores de Mapa
*   **Nombre:** Puntos de mapa
*   **Método:** `GET`
*   **URL:** `/api/v1/tourism/map-markers`
*   **Parámetros:** Ninguno.
*   **Campos importantes para Flutter:** `latitude`, `longitude`, `destination_id`.
*   **Pantalla:** Google Maps / vista de mapa.
*   **Observaciones:** Actualmente puede retornar vacío si los datos de lat/lng están marcados como PENDIENTE en el catálogo.

### Perfil de Usuario Demo
*   **Nombre:** Usuarios demo
*   **Método:** `GET`
*   **URL:** `/api/v1/users/demo`
*   **Parámetros:** Ninguno.
*   **Campos importantes para Flutter:** `user_id`, `name`, `email`.
*   **Pantalla:** Selector de perfiles (al no haber login real aún).

### Crear Reseña
*   **Nombre:** Registrar calificación
*   **Método:** `POST`
*   **URL:** `/api/v1/reviews`
*   **Body:** 
    ```json
    {
      "user_id": "U00001",
      "destination_id": "machu-picchu",
      "rating_general": 4.5,
      "review_text": "Excelente experiencia",
      "aspect_ratings": [
        {"aspect": "limpieza", "rating": 5.0}
      ]
    }
    ```
*   **Campos importantes para Flutter:** Enviar correctamente `rating_general` y la lista de `aspect_ratings`.
*   **Pantalla:** Formulario de calificación al finalizar visita o en detalle.

### Reseñas por Destino
*   **Nombre:** Reseñas de destino
*   **Método:** `GET`
*   **URL:** `/api/v1/reviews/destination/{destination_id}`
*   **Parámetros:** `destination_id` (path).
*   **Campos importantes para Flutter:** `rating_general`, `review_text`, `aspect_ratings`.
*   **Pantalla:** Sección de opiniones dentro del detalle del destino.

---

## 5. Campos clave que el frontend SÍ puede usar actualmente

### Destino (Detalle)
*   `destination_id`
*   `destination` (Nombre comercial)
*   `city`
*   `region`
*   `category`
*   `aspect_scores` (Objeto con: `accesibilidad`, `aforo_multitudes`, `alojamiento`, `atencion_servicio`, `atractivos`, `clima`, `costos`, `gastronomia`, `limpieza`, `seguridad`)
*   `context.weather_category` (Ej: "Favorable", "Desfavorable")
*   `context.crowd_level` (Ej: "Bajo", "Medio", "Alto")
*   `weather_detail.temp_prom`
*   `tourism_info.official_name`
*   `tourism_info.description`
*   `tourism_info.experience_type`
*   `tourism_info.gallery_images` (Lista de URLs)

### Recomendación Contextual (Home)
*   `rank` (Posición 1, 2, 3...)
*   `destination_id`
*   `destination`
*   `compatibility_percentage` (Float ej: 59.87 - ideal para barras circulares/lineales)
*   `label` (Ej: "Altamente recomendado")
*   `cover_image_url`
*   `short_explanation` (Texto explicativo del IA)

### Reseñas
*   `review_id`
*   `user_id`
*   `rating_general`
*   `review_text`
*   `aspect_ratings` (Lista de calificaciones por aspecto)

### Usuario
*   `user_id`
*   `name`
*   `email`

---

## 6. Campos que NO entrega el backend actualmente

El frontend NO debe esperar ni mapear como funcionales los siguientes datos en esta fase, debiendo ocultarlos o tratarlos como "mock/próximamente":

*   **Precios exactos:** No hay costo de entrada ni moneda en el backend.
*   **Horarios exactos:** Se provee texto general en `visitor_info_summary` del catálogo, pero no objetos de hora inicio/fin estructurados.
*   **Distancia en tiempo real:** El backend no calcula distancias desde la ubicación del móvil (se debe hacer en Flutter con `latitude`/`longitude`).
*   **Likes/Corazones de la comunidad:** No hay contador social implementado.
*   **Comentarios anidados/Respuestas a reseñas:** Las reseñas son planas.
*   **Fotos subidas por usuarios en reseñas:** Fase futura con Cloudinary.
*   **Foto de perfil de usuario real:** Fase futura con Cloudinary (usar avatares locales por defecto).
*   **Sistemas de pago / Reservas.**
*   **Autenticación JWT:** No hay login real con token, se usa `user_id` directo en las llamadas.
*   **Favoritos:** El modelo existe en BD, pero no hay endpoints públicos creados aún para marcarlos/desmarcarlos desde la app.

---

## 7. Matriz Backend → Frontend

| Dato del backend | Endpoint origen | Pantalla sugerida | Componente sugerido | Estado |
|---|---|---|---|---|
| `compatibility_percentage` | `/recommendations/contextual` | Home | Card de recomendación | **Disponible** |
| `aspect_scores.*` | `/destinations/{id}` | Detail | Gráficos de radar/barras | **Disponible** |
| `tourism_info.gallery_images`| `/destinations/{id}` | Detail | Carrusel de imágenes cabecera | **Disponible** |
| `weather_category` | `/destinations/{id}` | Detail | Chip/Icono del clima | **Disponible** |
| `activities_summary` | `/tourism/catalog/{id}` | Detail | Sección "¿Qué hacer?" | **Disponible** |
| `precio_entrada` | N/A | Detail | N/A | **No disponible** |
| `distancia_km` | N/A | Home/Detail | Calcular en cliente | **No disponible** |
| `review_image_url` | N/A | Feedback | N/A | **Futuro (Cloudinary)** |
| `user_avatar_url` | N/A | Perfil | Avatar local genérico | **Futuro (Cloudinary)** |

---

## 8. Ejemplos JSON Reales

### 1. `/api/v1/health`
```json
{
  "success": true,
  "message": "Operación exitosa",
  "data": {
    "status": "ok",
    "service": "PROXVEL Backend",
    "version": "1.0.0"
  }
}
```

### 2. `/api/v1/recommendations/contextual`
```json
{
  "success": true,
  "message": "Ranking contextual obtenido correctamente",
  "data": [
    {
      "rank": 1,
      "destination_id": "lago-titicaca",
      "destination": "Lago Titicaca",
      "city": "Puno",
      "cover_image_url": "https://commons.wikimedia.org/...",
      "compatibility_percentage": 59.87,
      "label": "Parcialmente recomendado",
      "final_score": 0.59868,
      "short_explanation": "El destino obtiene un score final de 59.87%. Combina afinidad base...",
      "tourism_summary": {
        "description": "Recurso natural emblemático del Perú...",
        "experience_type": "Natural, cultural y comunitario"
      }
    }
  ],
  "count": 1
}
```

### 3. `/api/v1/destinations/machu-picchu`
```json
{
  "success": true,
  "message": "Detalle de destino obtenido correctamente",
  "data": {
    "destination_id": "machu-picchu",
    "destination": "Machu Picchu",
    "region": "Cusco",
    "aspect_scores": {
      "accesibilidad": 0.50,
      "aforo_multitudes": 0.47,
      "alojamiento": 0.71,
      "atencion_servicio": 0.67,
      "atractivos": 0.61,
      "clima": 0.64,
      "costos": 0.53,
      "gastronomia": 0.74,
      "limpieza": 0.48,
      "seguridad": 0.50
    },
    "context": {
      "weather_category": "Desfavorable",
      "crowd_level": "Medio"
    },
    "tourism_info": {
      "official_name": "Parque Arqueológico Nacional De Machu Picchu",
      "description": "Parque arqueológico-cultural...",
      "gallery_images": [
        "url_1.jpg",
        "url_2.jpg"
      ]
    }
  }
}
```

### 4. `POST /api/v1/reviews` (Request)
```json
{
  "user_id": "U00001",
  "destination_id": "machu-picchu",
  "rating_general": 5.0,
  "review_text": "Lugar impresionante.",
  "aspect_ratings": [
    {
      "aspect": "atractivos",
      "rating": 5.0,
      "comment": "Paisaje excelente."
    }
  ]
}
```

---

## 9. Recomendación para auditoría del frontend

Con este documento generado, el siguiente paso crítico en el ciclo de vida de desarrollo es **auditar las pantallas y modelos de Flutter**:

1.  **Revisión de Modelos Dart:** Asegurar que los modelos en Flutter usen exactamente los mismos nombres de variables mostrados aquí (ej: `destination_id` y no `idDestino`).
2.  **Limpieza de UI:** Identificar qué elementos visuales del diseño en Figma/Flutter (como botones de "Reservar", precios, iconos de "Favoritos" si aún no hay backend) deben ocultarse temporalmente o deshabilitarse visualmente.
3.  **Aprovechamiento de Datos Ricos:** Validar que la UI del Detalle de Destino esté utilizando los datos enriquecidos que sí provee el backend, como los 10 scores de aspectos (`aspect_scores`) para generar gráficos tipo radar, y la lista de `gallery_images` para carruseles, garantizando que el diseño represente el valor real de los datos calculados.
