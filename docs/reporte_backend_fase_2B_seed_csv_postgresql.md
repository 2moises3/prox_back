# Reporte Backend Fase 2B — Seeder de CSV a PostgreSQL

**Fecha:** 2026-06-09
**Estado:** ✅ Completado exitosamente

---

## 1. Objetivo de la Fase
Implementar los scripts de inicialización (Seeder) para leer los datos maestros desde los 5 archivos CSV actuales en `app/data/` y persistirlos en la nueva base de datos PostgreSQL, utilizando SQLAlchemy ORM. Todo esto asegurando la idempotencia (poder ejecutar el script repetidas veces sin duplicar datos) y manteniendo intactas las tablas operativas (usuarios, reseñas) para fases futuras.

---

## 2. Archivos Creados
Se crearon tres utilidades en `app/scripts/`:

1. `seed_database.py`: Lee los CSV utilizando el módulo existente `csv_loader.py` y puebla la base de datos de manera controlada.
2. `check_database_counts.py`: Realiza validación de integridad contando las filas en las 14 tablas (metodológicas y operativas).
3. `reset_seeded_tables.py`: Utilidad para borrar de forma segura únicamente los datos de las tablas metodológicas sin alterar las operativas.

*(Nota: No se modificaron repositorios, endpoints ni el flujo de CSV actual).*

---

## 3. CSV Procesados
Se leyeron correctamente los 5 archivos originales:
- `matriz_absa_normalizada.csv`
- `clima_scores.csv`
- `aforo_scores.csv`
- `ranking_contextual_final.csv`
- `destinations_catalog.csv`

---

## 4. Tablas Cargadas
Únicamente se permitió poblar las 6 tablas metodológicas del núcleo de tesis:
- `destinations`
- `tourism_catalog`
- `destination_aspect_scores`
- `climate_scores`
- `crowd_scores`
- `contextual_rankings`

---

## 5. Orden de Carga
Se respetó rigurosamente el modelo relacional (de lo general a lo dependiente):
1. **Limpieza controlada** (borrado en orden inverso).
2. **Destinos únicos** consolidados desde todos los CSV (`destinations`).
3. **Catálogo Oficial MINCETUR** (`tourism_catalog`).
4. **Scores ABSA** (`destination_aspect_scores`).
5. **Contexto Climático** (`climate_scores`).
6. **Contexto de Aforo** (`crowd_scores`).
7. **Ranking Contextual** (`contextual_rankings`).

---

## 6. Estrategia de Upsert / Idempotencia
Se implementó un diseño 100% idempotente:
- Para `destinations`: Se utilizó `INSERT ... ON CONFLICT DO NOTHING` ya que es la entidad padre principal y otras entidades futuras (como `reviews` o `favorites`) podrían depender de ella vía Foreign Key. De esta forma, si el destino ya existe, no se interrumpe y se previene violación de restricciones.
- Para las 5 tablas metodológicas dependientes: Se efectúa un `DELETE` controlado previo al insert. Esto asegura que los scores precalculados se refresquen completamente a su estado maestro de CSV y previene duplicados.

---

## 7. Manejo de Nulos y PENDIENTE
Se reutilizaron las funciones de `app.utils.normalizers`:
- Cadenas vacías, `"NaN"`, y `"PENDIENTE"` se detectan y normalizan a `None` de forma segura mediante wrappers tipados (`safe_float` y `safe_int`).
- Esto previno errores de inserción en columnas Float (como `latitude` y `longitude` del catálogo).
- Los identificadores de destino `destination_id` se normalizaron automáticamente usando `generate_destination_id()` para asegurar que entidades dispersas en los CSV coincidan exactamente en PostgreSQL (ej. "Machu Picchu" -> "machu-picchu").

---

## 8. Conteos Finales por Tabla
El volcado coincide de manera perfecta con los reportes de Fase 1.

**Tablas Metodológicas:**
| Tabla | Total Registros |
|-------|-----------------|
| `destinations` | 3 |
| `tourism_catalog` | 3 |
| `destination_aspect_scores` | 3 |
| `climate_scores` | 36 |
| `crowd_scores` | 766 |
| `contextual_rankings` | 9000 |

---

## 9. Confirmación de Tablas Operativas NO Modificadas
Se confirma que las tablas destinadas a recolección en tiempo de ejecución permanecen inalteradas y en cero.

**Tablas Operativas:**
| Tabla | Total Registros |
|-------|-----------------|
| `users` | 0 |
| `traveler_profiles` | 0 |
| `favorites` | 0 |
| `reviews` | 0 |
| `review_aspect_ratings` | 0 |
| `monthly_review_batches` | 0 |
| `model_update_runs` | 0 |
| `visits` | 0 |

---

## 10. Resultado de Ejecutar el Seeder (`python -m app.scripts.seed_database`)
```text
2026-06-09 01:25:29 | INFO    | Cargando CSV desde disco...
2026-06-09 01:25:29 | INFO    | Limpiando tablas metodológicas (Borrado Controlado)...
2026-06-09 01:25:29 | INFO    | Procesando destinations...
2026-06-09 01:25:29 | INFO    | Procesando tourism_catalog...
2026-06-09 01:25:29 | INFO    | Procesando destination_aspect_scores...
2026-06-09 01:25:29 | INFO    | Procesando climate_scores...
2026-06-09 01:25:29 | INFO    | Procesando crowd_scores...
2026-06-09 01:25:29 | INFO    | Procesando contextual_rankings...
2026-06-09 01:25:39 | INFO    | ¡Seeding completado exitosamente!
```

---

## 11. Resultado de `check_database_counts` (Idempotencia probada)
Ejecutar el seeder repetidas veces arroja los mismos resultados de conteo consistentemente, y no produce duplicados en PostgreSQL, confirmando la idempotencia exitosa.

---

## 12. Resultado de `pytest`
```text
======================== 14 passed, 1 warning in 1.77s ========================
```
Los tests no han sufrido ninguna alteración. El fallback a CSV sigue funcionando perfectamente porque el `TestClient` sigue cargando la memoria.

---

## 13. Resultado de `python run.py`
El backend levanta sin fallas, carga los 5 CSV a memoria exitosamente y los 10 endpoints responden correctamente a través de HTTP y Swagger.

---

## 14. Consultas SQL Recomendadas para DataGrip
Para validar directamente en PostgreSQL:

**1. Comprobar que los scores base fueron cargados:**
```sql
SELECT 
  d.destination, 
  a.clima, 
  a.costos, 
  a.seguridad
FROM destinations d
JOIN destination_aspect_scores a ON d.destination_id = a.destination_id;
```

**2. Comprobar que el catálogo maneja los campos pendientes como NULL:**
```sql
SELECT 
  destination_id, 
  category, 
  latitude, 
  longitude 
FROM tourism_catalog;
```

**3. Comprobar la integridad de los rankings:**
```sql
SELECT user_id, rank, score_final_fase4, etiqueta_final 
FROM contextual_rankings 
WHERE destination_id = 'machu-picchu' 
ORDER BY score_final_fase4 DESC 
LIMIT 5;
```

---

## 15. Riesgos o Advertencias
1. **Memoria (RAM):** La tabla `contextual_rankings` contiene 9000 registros y fue volcada utilizando inserción por lotes (`bulk_save_objects`). A medida que aumenten las filas generadas por los modelos futuros, este script requerirá una paginación si se siguen volcando desde CSV.
2. **Duplicidad Transitoria:** Si algún CSV cambia la convención de mayúsculas ("MachuPicchu" vs "Machu Picchu"), `generate_destination_id` asimilará las diferencias sin crear IDs duplicados, pero el string del nombre (`destination`) conservará el del primer CSV que lo registró.

---

## 16. Qué queda para Fase 2C
En la **Fase 2C** procederemos a:
1. **Refactorizar Repositorios:** Actualizar `destination_repository`, `ranking_repository` y `tourism_repository` para que lean directamente desde la base de datos PostgreSQL utilizando sesiones de SQLAlchemy (`Session`).
2. **Implementar el Fallback Transparente:** La lógica debe intentar consultar la DB y, si falla o está vacía (aunque ya sabemos que tiene datos), redirigir a los CSV en memoria.
3. **Mantener Contratos JSON:** No se alterarán los formatos de respuesta hacia el Frontend Flutter.
