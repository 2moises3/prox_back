# Guía Completa de Integración Flutter ↔ Backend PROXVEL

Este documento detalla los lineamientos técnicos y ejemplos prácticos para conectar la aplicación móvil PROXVEL (Flutter) con el backend FastAPI.

---

## 1. Configuración de BASE_URL

La `BASE_URL` debe configurarse diferente según el entorno donde corres la aplicación Flutter:

| Entorno | BASE_URL | Notas |
|---------|----------|-------|
| **iOS Simulator** (local) | `http://127.0.0.1:8000` | Localhost standard |
| **Android Emulator** (local) | `http://10.0.2.2:8000` | **IMPORTANTE**: No usar `localhost`, usar `10.0.2.2` |
| **Dispositivo Físico** (red local) | `http://<IP_LOCAL_DE_LA_PC>:8000` | Ejemplo: `http://192.168.1.100:8000` |
| **Producción** | `https://api.proxvel.com` | HTTPS obligatorio (por confirmar) |

### ⚠️ Advertencias Críticas

**Android Emulator:**
- El emulador corre en VM aislada
- `localhost` o `127.0.0.1` apuntan al emulador mismo, no a tu PC
- Usar **`10.0.2.2`** (alias especial que Android proporciona para "host")
- Ejemplo correcto: `http://10.0.2.2:8000/api/v1/health`
- Ejemplo incorrecto: ❌ `http://localhost:8000/api/v1/health`

**Dispositivo Físico:**
- PC y dispositivo deben estar en la **misma red Wi-Fi**
- Obtener IP local de la PC:
  - Windows: `ipconfig` → buscar "IPv4 Address" (ej. `192.168.1.100`)
  - Mac/Linux: `ifconfig` → buscar inet (ej. `192.168.1.100`)
- Verificar conectividad: Abre navegador en móvil → `http://192.168.1.100:8000/docs`

**CORS:**
- Backend permite `CORS_ORIGINS=*` en desarrollo
- En producción, restringir a dominios específicos

---

## 2. Tabla de Endpoints por Pantalla Flutter

| Pantalla Flutter | Endpoint Backend | Método | Descripción | User ID |
|:---|:---|:---:|:---|:---|
| **HomeScreen** | `/api/v1/recommendations/contextual` | GET | Mostrar recomendaciones personalizadas "Para ti" | ✓ `user_id` param |
| **HomeScreen** | `/api/v1/data/status` | GET | Verificar modo operativo (opcional, para debugging) | ✗ |
| **SearchScreen** | `/api/v1/recommendations/search` | GET | Buscar destinos por nombre o palabra clave | ✗ |
| **SearchScreen** | `/api/v1/destinations` | GET | Listar todos los destinos disponibles (3 en piloto: Machu Picchu, Lago Titicaca, Circuito Mágico) | ✗ |
| **DestinationDetailScreen** | `/api/v1/destinations/{destination_id}` | GET | Detalle completo: scores ABSA, clima, aforo, info turística | ✗ |
| **TourismInfoBlock** | `/api/v1/tourism/catalog/{destination_id}` | GET | Ficha turística oficial (MINCETUR): descripción, actividades, accesibilidad, etc. | ✗ |
| **MapScreen** | `/api/v1/tourism/map-markers` | GET | Coordenadas (lat/lng) para renderizar en mapa | ✗ |
| **FeedbackScreen** | `/api/v1/reviews` | POST | Enviar reseña/rating del usuario (con ratings por aspecto) | ✓ `user_id` body |
| **ProfileScreen** | `/api/v1/users/{user_id}` | GET | Mostrar datos del usuario (demo: U00001, U00002, U00003) | ✓ `user_id` path |
| **ReviewsHistoryScreen** | `/api/v1/reviews/user/{user_id}` | GET | Listar reseñas del usuario actual | ✓ `user_id` path |
| **DestinationReviewsScreen** | `/api/v1/reviews/destination/{destination_id}` | GET | Listar reseñas de un destino (feedback comunitario) | ✗ |
| **Admin Panel** (no Flutter) | `/api/v1/admin/training-batches` | GET/POST | Exportar reseñas pendientes a CSV (solo backend/admin) | ✗ |

---

## 3. Ejemplos de Request / Response

### 3.1 Recomendaciones Contextuales (GET)

**Request:**
```
GET /api/v1/recommendations/contextual?user_id=U00001&limit=10
Host: 127.0.0.1:8000
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "rank": 1,
      "destination_id": "machu-picchu",
      "destination": "Machu Picchu",
      "city": "Machupicchu",
      "region": "Cusco",
      "category": "Manifestaciones Culturales",
      "cover_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Machu_Picchu.png",
      "compatibility_percentage": 95.5,
      "label": "Altamente Recomendado",
      "final_score": 92.0,
      "short_explanation": "Tu presupuesto coincide y te gustan las zonas arqueológicas. Clima favorable esta temporada.",
      "aspect_scores": {
        "accesibilidad": 78.0,
        "aforo_multitudes": 72.0,
        "alojamiento": 85.0,
        "atractivos": 95.0,
        "costos": 88.0
      },
      "context": {
        "weather_score": 88.0,
        "crowd_score": 85.0,
        "weather_category": "Favorable",
        "crowd_level": "Moderado"
      },
      "tourism_summary": {
        "description": "Parque arqueológico-cultural ubicado al noreste de Cusco...",
        "experience_type": "Arqueológico, cultural y natural",
        "cover_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Machu_Picchu.png"
      }
    },
    {
      "rank": 2,
      "destination_id": "lago-titicaca",
      "destination": "Lago Titicaca",
      "city": "Puno",
      "region": "Puno",
      "category": "Sitios Naturales",
      "cover_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Lago_Titicaca,_Puno.JPG",
      "compatibility_percentage": 87.3,
      "label": "Recomendado",
      "final_score": 85.0,
      "short_explanation": "Experiencia natural única. Actividades acuáticas y culturales disponibles.",
      "aspect_scores": {
        "accesibilidad": 82.0,
        "aforo_multitudes": 68.0,
        "alojamiento": 75.0,
        "atractivos": 90.0,
        "costos": 80.0
      },
      "context": {
        "weather_score": 82.0,
        "crowd_score": 75.0,
        "weather_category": "Templado",
        "crowd_level": "Bajo"
      },
      "tourism_summary": {
        "description": "Recurso natural emblemático del Perú...",
        "experience_type": "Natural, cultural y comunitario",
        "cover_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Lago_Titicaca,_Puno.JPG"
      }
    }
  ],
  "message": "Ranking contextual obtenido correctamente"
}
```

**Parámetros:**
- `user_id` (opcional): ID del usuario (ej: `U00001`). Si no se proporciona, retorna primer usuario demo.
- `limit` (opcional, default 10): Máximo 100 resultados.
- `city` (opcional): Filtro por ciudad (preparado para futuro).

**Campos principales:**
- `destination`: Nombre del destino (no `destination_name`)
- `compatibility_percentage`: Porcentaje de compatibilidad (no `compatibilidad_final`)
- `label`: Etiqueta descriptiva (no `etiqueta_final`)
- `final_score`: Score final de ranking (no `score_final_fase4`)
- `short_explanation`: Explicación breve (no `explicacion_final`)

---

### 3.2 Búsqueda de Destinos (GET)

**Request:**
```
GET /api/v1/recommendations/search?query=machu&limit=5
Host: 127.0.0.1:8000
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "destination_id": "machu-picchu",
      "destination": "Machu Picchu",
      "city": "Machupicchu",
      "region": "Cusco",
      "category": "Manifestaciones Culturales",
      "cover_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Machu_Picchu.png",
      "compatibility_percentage": 95.5,
      "final_score": 92.0
    }
  ],
  "message": "Resultados de búsqueda obtenidos correctamente"
}
```

**Notas:**
- Búsqueda case-insensitive en nombre de destino y ciudad
- Retorna resultados ordenados por compatibilidad descendente
- Campo `destination` contiene el nombre del destino (no `destination_name`)

---

### 3.3 Detalle de Destino (GET)

**Request:**
```
GET /api/v1/destinations/machu-picchu
Host: 127.0.0.1:8000
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "destination_id": "machu-picchu",
    "destination": "Machu Picchu",
    "city": "Machupicchu",
    "region": "Cusco",
    "category": "Manifestaciones Culturales",
    "aspect_scores": {
      "accesibilidad": 78.0,
      "aforo_multitudes": 72.0,
      "alojamiento": 85.0,
      "atencion_servicio": 88.0,
      "atractivos": 95.0,
      "clima": 82.0,
      "costos": 88.0,
      "gastronomia": 82.0,
      "limpieza": 90.0,
      "seguridad": 92.0
    },
    "context": {
      "weather_score": 82.0,
      "crowd_score": 75.0,
      "weather_category": "Favorable",
      "crowd_level": "Moderado"
    },
    "weather_detail": {
      "month_name": "Junio",
      "temp_prom": 18.5,
      "pp": 3.2,
      "clima_categoria": "Favorable",
      "score_clima": 82.0
    },
    "crowd_detail": {
      "periodo": "2026-06",
      "visitantes_mes": 45000,
      "aforo_normalizado": 72.0,
      "nivel_aforo": "Moderado",
      "score_aforo_base": 75.0
    },
    "tourism_info": {
      "official_name": "Parque Arqueológico Nacional De Machu Picchu",
      "description": "Parque arqueológico-cultural ubicado al noreste de la ciudad del Cusco...",
      "experience_type": "Arqueológico, cultural y natural",
      "gallery_images": [
        "https://commons.wikimedia.org/wiki/Special:FilePath/Machu_Picchu.png",
        "https://commons.wikimedia.org/wiki/Special:FilePath/Machu_Picchu,_Peru.jpg"
      ],
      "official_source_name": "Inventario de Recursos Turísticos del Perú - MINCETUR",
      "official_source_url": "https://consultasenlinea.mincetur.gob.pe/fichaInventario/index.aspx?cod_Ficha=917"
    }
  },
  "message": "Destino obtenido correctamente"
}
```

**Campos principales:**
- `aspect_scores`: 10 aspectos ABSA (accesibilidad, aforo_multitudes, alojamiento, etc.)
- `weather_detail`: Contexto climático (temperatura promedio, precipitación, categoría)
- `crowd_detail`: Contexto de aforo (visitantes mensuales, nivel de ocupación)
- `tourism_info`: Ficha turística oficial de MINCETUR (descripción, actividades, accesibilidad)

---

### 3.4 Catálogo Turístico Oficial (GET)

**Request:**
```
GET /api/v1/tourism/catalog/machu-picchu
Host: 127.0.0.1:8000
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "destination_id": "machu-picchu",
    "destination": "Machu Picchu",
    "official_name": "Parque Arqueológico Nacional De Machu Picchu",
    "department": "Cusco",
    "province": "Urubamba",
    "district": "MACHUPICCHU",
    "city": "Machupicchu",
    "region": "Cusco",
    "category": "Manifestaciones Culturales",
    "type": "Sitios Arqueológicos",
    "subtype": "Parques arqueológicos",
    "hierarchy": 4,
    "altitude_m": 2340,
    "description": "Parque arqueológico-cultural ubicado al noreste de la ciudad del Cusco. Integra patrimonio arqueológico, paisaje, flora, fauna y arquitectura inca en armonía con la naturaleza...",
    "experience_type": "Arqueológico, cultural y natural",
    "visitor_info_summary": "Visita durante todo el año. La ficha registra ingreso con boleto y horarios de visita entre 06:00 a.m. y 05:00 p.m.",
    "activities_summary": "Toma de fotografías y filmaciones, observación de paisaje, observación de flora y fauna, observación de aves, rituales místicos o tradicionales y caminata/trekking.",
    "accessibility_summary": "La ficha indica recorridos asistidos en la parte baja para visitantes con discapacidad, respetando el reglamento de la llaqta de Machupicchu.",
    "latitude": -13.1631,
    "longitude": -72.5450,
    "geofence_radius_m": 5000.0,
    "cover_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Machu_Picchu.png",
    "gallery_images": [
      "https://commons.wikimedia.org/wiki/Special:FilePath/Machu_Picchu,_Peru.jpg",
      "https://commons.wikimedia.org/wiki/Special:FilePath/80_-_Machu_Picchu_-_Juin_2009_-_edit.jpg"
    ],
    "image_source": "Wikimedia Commons",
    "official_source_name": "Inventario de Recursos Turísticos del Perú - MINCETUR",
    "official_source_code": "917",
    "official_source_url": "https://consultasenlinea.mincetur.gob.pe/fichaInventario/index.aspx?cod_Ficha=917",
    "data_status": "VALIDADO_PARCIAL_PDF_OFICIAL"
  },
  "message": "Catálogo turístico obtenido correctamente"
}
```

**Fuente:** Inventario de Recursos Turísticos del Perú - MINCETUR (Ministerio de Comercio Exterior y Turismo, Perú).

**Campos principales:**
- `official_name`: Nombre oficial registrado en MINCETUR
- `visitor_info_summary`: Información de visita y horarios
- `activities_summary`: Actividades turísticas disponibles
- `accessibility_summary`: Acceso para personas con discapacidad
- `latitude`, `longitude`: Coordenadas exactas para mapeo
- `gallery_images`: Galería de imágenes del recurso

---

### 3.5 Crear Reseña (POST)

**Request:**
```
POST /api/v1/reviews
Content-Type: application/json
Host: 127.0.0.1:8000
```

**Body:**
```json
{
  "user_id": "U00001",
  "destination_id": "machu-picchu",
  "rating_general": 5.0,
  "review_text": "Experiencia increíble. Vistas panorámicas espectaculares. Muy recomendado a todos los viajeros.",
  "aspect_ratings": [
    {
      "aspect": "atractivos",
      "rating": 5.0,
      "comment": "Paisaje y monumentos fascinantes"
    },
    {
      "aspect": "accesibilidad",
      "rating": 3.0,
      "comment": "Subida exigente, requiere buena condición física"
    },
    {
      "aspect": "seguridad",
      "rating": 5.0,
      "comment": "Muy seguro, buena vigilancia"
    },
    {
      "aspect": "limpieza",
      "rating": 4.5,
      "comment": "Muy limpio, excelente mantenimiento"
    }
  ]
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "review_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "U00001",
    "destination_id": "machu-picchu",
    "rating_general": 5.0,
    "status": "pending_processing",
    "created_at": "2026-06-09T14:35:22.123456Z",
    "aspect_ratings": [
      {
        "aspect": "atractivos",
        "rating": 5.0,
        "comment": "Paisaje y monumentos fascinantes"
      }
    ]
  },
  "message": "Reseña registrada correctamente"
}
```

**Restricciones de Validación:**
- `user_id`: Debe existir en BD (ej: U00001, U00002, U00003 en demo)
- `destination_id`: Debe existir en catálogo
- `rating_general`: Entre 1.0 y 5.0 (decimal)
- `aspect_ratings`: Mínimo 1 aspecto, máximo 5
- `review_text`: Máximo 1000 caracteres

---

### 3.6 Obtener Usuarios Demo (GET)

**Request:**
```
GET /api/v1/users/demo
Host: 127.0.0.1:8000
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "user_id": "U00001",
      "name": "Usuario Demo 1",
      "email": "demo1@proxvel.local"
    },
    {
      "user_id": "U00002",
      "name": "Usuario Demo 2",
      "email": "demo2@proxvel.local"
    },
    {
      "user_id": "U00003",
      "name": "Usuario Demo 3",
      "email": "demo3@proxvel.local"
    }
  ],
  "message": "Usuarios demo obtenidos"
}
```

---

## 4. Manejo de Errores

El backend retorna errores HTTP estándar con estructura JSON consistente:

### 4.1 Error 404: Recurso No Encontrado

**Caso:** Usuario o destino no existe

```
GET /api/v1/users/USER_INVALIDO
```

**Response (404 Not Found):**
```json
{
  "detail": "Usuario no encontrado"
}
```

**En Flutter:** 
```dart
if (response.statusCode == 404) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text('Usuario o destino no encontrado'))
  );
}
```

---

### 4.2 Error 422: Validación Falló

**Caso:** Rating general fuera de rango (ej. 6.0)

```
POST /api/v1/reviews
Body: {"rating_general": 6.0, ...}
```

**Response (422 Unprocessable Entity):**
```json
{
  "detail": [
    {
      "loc": ["body", "rating_general"],
      "msg": "ensure this value is less than or equal to 5.0",
      "type": "value_error.number.not_le"
    }
  ]
}
```

**En Flutter:**
```dart
if (response.statusCode == 422) {
  var errors = jsonDecode(response.body)['detail'];
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text('Error de validación: ${errors[0]['msg']}'))
  );
}
```

---

### 4.3 Error 500: Error Interno (Improbable)

**Caso:** Fallback CSV falló (escenario muy raro)

```
GET /api/v1/destinations
```

**Response (500 Internal Server Error):**
```json
{
  "detail": "Internal server error"
}
```

**En Flutter:**
```dart
if (response.statusCode >= 500) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text('Error del servidor. Intenta más tarde.'))
  );
}
```

---

### 4.4 Error de Conexión

**Caso:** Backend no responde (máquina no está en red, puerto bloqueado, etc.)

```dart
try {
  var response = await http.get(
    Uri.parse('$BASE_URL/api/v1/health'),
    headers: {'Content-Type': 'application/json'},
  ).timeout(
    Duration(seconds: 5),
    onTimeout: () => http.Response('Error', 0),
  );
  
  if (response.statusCode == 0) {
    // Sin conexión
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Sin conexión. Verifica IP del servidor.'))
    );
  }
} catch (e) {
  print('Error: $e');
}
```

---

## 5. Orden Recomendado de Integración

Sigue este orden para minimizar dependencias y facilitar testing progresivo:

### **Fase 1: Setup Base (Día 1)**
1. ✅ Configurar `BASE_URL` en `.env` o `main.dart` según entorno
2. ✅ Crear servicio HTTP singleton (`http_service.dart`)
3. ✅ Prueba simple: `GET /api/v1/health` y `GET /api/v1/data/status`
4. ✅ Verificar modo operativo (database vs csv_fallback)

### **Fase 2: Recomendaciones (Día 2-3)**
1. ✅ Integrar `GET /api/v1/recommendations/contextual?user_id=U00001` en HomeScreen
2. ✅ Parsejar respuesta con modelos Dart (null-safe)
3. ✅ Renderizar lista con FutureBuilder
4. ✅ Agregar indicador de carga (CircularProgressIndicator)

### **Fase 3: Búsqueda (Día 3-4)**
1. ✅ Integrar `GET /api/v1/recommendations/search?query=...` en SearchScreen
2. ✅ Implementar debounce en campo de búsqueda (500ms)
3. ✅ Mostrar resultados en tiempo real
4. ✅ Manejar caso vacío (lista sin resultados)

### **Fase 4: Detalles (Día 4-5)**
1. ✅ Integrar `GET /api/v1/destinations/{id}` en DestinationDetailScreen
2. ✅ Integrar `GET /api/v1/tourism/catalog/{id}` en TourismInfoBlock
3. ✅ Mostrar scores ABSA en charts (barchart, radarchart)
4. ✅ Mostrar clima/aforo en tablas o cards

### **Fase 5: Feedback (Día 5-6)**
1. ✅ Crear formulario de reseña con validación
2. ✅ Integrar `POST /api/v1/reviews` en FeedbackScreen
3. ✅ Manejar errores 404 (usuario/destino no encontrado) y 422 (validación)
4. ✅ Mostrar confirmación: "Reseña enviada correctamente"

### **Fase 6: Perfil (Día 6)**
1. ✅ Integrar `GET /api/v1/users/{user_id}` en ProfileScreen
2. ✅ Mostrar datos del usuario actual (demo)
3. ✅ Integrar `GET /api/v1/reviews/user/{user_id}` para historial de reseñas

### **Fase 7: Pulido (Día 7)**
1. ✅ Testing en Android Emulator y Dispositivo Físico
2. ✅ Optimizar imágenes y caché
3. ✅ Agregar offline mode si es necesario (local SQLite)
4. ✅ Documentar errores encontrados

---

## 6. Ejemplos de Código Dart (Pseudo-código)

### 6.1 Servicio HTTP Singleton

```dart
class HttpService {
  static const String baseUrl = "http://10.0.2.2:8000"; // Android
  // static const String baseUrl = "http://127.0.0.1:8000"; // iOS
  // static const String baseUrl = "http://192.168.1.100:8000"; // Físico
  
  final http.Client _httpClient = http.Client();
  
  Future<List<Destination>> getRecommendations(String userId) async {
    try {
      var response = await _httpClient.get(
        Uri.parse('$baseUrl/api/v1/recommendations/contextual?user_id=$userId'),
        headers: {'Content-Type': 'application/json'},
      ).timeout(Duration(seconds: 10));
      
      if (response.statusCode == 200) {
        var jsonData = jsonDecode(response.body);
        var recommendations = (jsonData['data'] as List)
          .map((d) => Destination.fromJson(d))
          .toList();
        return recommendations;
      } else {
        throw Exception('Error: ${response.statusCode}');
      }
    } catch (e) {
      print('Error fetching recommendations: $e');
      rethrow;
    }
  }
}
```

### 6.2 Enviar Reseña

```dart
Future<void> submitReview(ReviewData review) async {
  try {
    var response = await _httpClient.post(
      Uri.parse('$baseUrl/api/v1/reviews'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(review.toJson()),
    );
    
    if (response.statusCode == 201) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Reseña enviada correctamente'))
      );
    } else if (response.statusCode == 404) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Usuario o destino no encontrado'))
      );
    } else if (response.statusCode == 422) {
      var errors = jsonDecode(response.body)['detail'];
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error de validación'))
      );
    }
  } catch (e) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Error de conexión'))
    );
  }
}
```

---

## 7. Testing de Conectividad

### Prueba local (Postman / curl)

```bash
# Verificar salud
curl -X GET "http://127.0.0.1:8000/api/v1/health"

# Obtener recomendaciones
curl -X GET "http://127.0.0.1:8000/api/v1/recommendations/contextual?user_id=U00001"

# Crear reseña
curl -X POST "http://127.0.0.1:8000/api/v1/reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "U00001",
    "destination_id": "machu-picchu",
    "rating_general": 5.0,
    "review_text": "Excelente",
    "aspect_ratings": [
      {"aspect": "atractivos", "rating": 5.0, "comment": "Muy bueno"}
    ]
  }'
```

### En Flutter (riverpod / provider)

```dart
final recommendationsProvider = FutureProvider.autoDispose.family(
  (ref, String userId) async {
    final service = ref.watch(httpServiceProvider);
    return service.getRecommendations(userId);
  },
);

// En UI:
Consumer(
  builder: (context, ref, child) {
    var recommendations = ref.watch(recommendationsProvider('U00001'));
    
    return recommendations.when(
      data: (data) => ListView(
        children: data.map((d) => DestinationCard(d)).toList(),
      ),
      loading: () => CircularProgressIndicator(),
      error: (err, stack) => Text('Error: $err'),
    );
  },
)
```

---

## 8. Resumen de Configuración Rápida

| Punto | Acción |
|-------|--------|
| 1. Backend corriendo | `python run.py` (en proxvel_backend/) |
| 2. PostgreSQL encendido | `docker start proxvel_postgres` |
| 3. BASE_URL en Flutter | `http://10.0.2.2:8000` (Android Emulator) |
| 4. Verificar salud | GET `http://10.0.2.2:8000/api/v1/health` |
| 5. Consumir endpoints | Seguir tabla de endpoints § 2 |
| 6. Manejar errores | Códigos HTTP 404, 422, conexión |
| 7. Testing | Postman / curl primero, luego Flutter |
