# Changelog — SeñalCDMX API

## [2026-04-08] Migración a esquema NeonDB + corrección de layer_fetcher

---

### Contexto

El equipo de frontend definió el esquema real de la base de datos en NeonDB (PostgreSQL serverless). El esquema difiere del modelo inicial del backend: los resultados de IA van en una tabla separada (`procesamiento_ia`), la tabla principal se llama `reportes` (no `reports`), y los campos de dirección son más simples (`direccion_aprox` en lugar de `street` + `ext_number` + etc.).

---

### Archivos modificados

#### `app/models.py` — Reescritura completa

**Antes:** Un solo modelo `Report` mapeado a la tabla `reports`, con campos mezclados de dirección, coordenadas y resultados de IA en la misma tabla.

**Ahora:** 10 modelos que mapean exactamente el esquema NeonDB:

| Modelo | Tabla | Descripción |
|--------|-------|-------------|
| `Reporte` | `reportes` | Datos del reporte ciudadano |
| `ProcesamientoIA` | `procesamiento_ia` | Resultados del análisis con Watson x |
| `Usuario` | `usuarios` | Ciudadanos y funcionarios |
| `Evidencia` | `evidencias` | Fotos adjuntas al reporte |
| `DocumentoTecnico` | `documentos_tecnicos` | PDFs generados por IA |
| `HistorialEstado` | `historial_estado` | Auditoría de cambios de estado |
| `RespuestaGobierno` | `respuestas_gobierno` | Respuestas oficiales al ciudadano |
| `EntidadGobierno` | `entidades_gobierno` | Dependencias de gobierno |
| `AsignacionGobierno` | `asignaciones_gobierno` | Asignación de reportes a entidades |
| `MetricaDiaria` | `metricas_diarias` | KPIs diarios para el dashboard |
| `CategoriaConfig` | `categorias_config` | Catálogo de categorías configurables |

Cambios clave en `Reporte`:
- Campos de dirección: `direccion_aprox` (texto libre) en lugar de `street` + `ext_number` + `postal_code` + etc.
- Coordenadas: `latitud` / `longitud` (tipo `Numeric`) en lugar de `lat` / `lng`
- Estado: campo `estado` (en lugar de `status`)
- Nuevo campo `codigo` — identificador legible generado en el endpoint (`RPT-2025-00042`)
- Eliminada columna `location` de PostGIS (Geometry) — NeonDB usa lat/lng simples
- Eliminadas columnas de resultados de IA (`priority`, `analysis`, `layers_summary`) — ahora viven en `ProcesamientoIA`

Relaciones SQLAlchemy definidas entre `Reporte` y sus tablas relacionadas via `relationship()`.

---

#### `app/schemas.py` — Reescritura completa

**Antes:** `ReportCreate` con campos de dirección granulares; `ReportResponse` con resultados de IA aplanados.

**Ahora:**

**`ReportCreate`** — lo que envía el frontend:
```json
{
  "descripcion": "string (requerido)",
  "descripcion_audio": "string | null",
  "direccion_aprox": "string | null",
  "alcaldia": "string | null",
  "colonia": "string | null",
  "ciudad": "string (default: Ciudad de México)",
  "latitud": "float | null",
  "longitud": "float | null",
  "fuente_input": "string (default: web)",
  "tiene_imagen": "bool (default: false)",
  "usuario_id": "int | null"
}
```

**`ReportCreatedResponse`** — ahora incluye `codigo`:
```json
{ "report_id": 42, "codigo": "RPT-2025-00042", "status": "processing" }
```

**`ProcesamientoIAResponse`** — objeto anidado nuevo con todos los campos de IA:
- `tipo_problema` — tipo específico (ej. `"inundacion"`, `"bache"`)
- `categoria_detectada` — `"riesgos"` | `"movilidad"`
- `prioridad_asignada` — `"alta"` | `"media"` | `"baja"`
- `confianza_pct` — porcentaje de confianza del clasificador
- `probabilidad_atencion` — el porcentaje visible en el frontend (ej. 88%)
- `justificacion` — narrativa del análisis
- `recomendacion_gobierno` — acciones propuestas
- `contexto_urbano` — hallazgos geoespaciales en texto

**`ReportResponse`** — incluye el objeto `ia` anidado (null mientras procesa):
```json
{
  "report_id": 1,
  "codigo": "RPT-2025-00001",
  "status": "ready",
  "latitud": 19.432,
  "longitud": -99.133,
  "alcaldia": "Iztapalapa",
  "created_at": "2025-04-08T18:30:00",
  "ia": {
    "prioridad_asignada": "alta",
    "probabilidad_atencion": 88.0,
    "justificacion": "...",
    ...
  }
}
```

**`ReportListItem`** — nuevo schema para el endpoint de lista (`GET /reports`).

---

#### `app/database.py` — Conexión SSL para NeonDB

**Antes:** `create_engine(settings.database_url)` — conexión sin configuración SSL.

**Ahora:** NeonDB requiere SSL y su URL incluye parámetros que psycopg2 no soporta (`channel_binding=require`). Solución:

```python
# Se limpia la URL (se quitan query params)
clean_url = urlunparse(parsed._replace(query=""))

# SSL se configura explícitamente via connect_args
create_engine(clean_url, connect_args={"sslmode": "require"}, pool_pre_ping=True)
```

`pool_pre_ping=True` reconecta automáticamente si NeonDB cierra la conexión por inactividad (comportamiento normal en serverless).

---

#### `app/main.py` — Nuevos endpoints y lógica de creación

**Antes:** 2 endpoints (`POST /reports`, `GET /reports/{id}`). Creaba `models.Report` directamente con `Base.metadata.create_all()`.

**Ahora:**

- Eliminado `Base.metadata.create_all()` — la DB ya existe en NeonDB con el esquema definido.
- `POST /reports`: crea `models.Reporte`, genera `codigo` después del insert (`RPT-{año}-{id:05d}`), dispara pipeline.
- `GET /reports/{id}`: consulta `Reporte` + `ProcesamientoIA` via relación SQLAlchemy, construye respuesta con objeto `ia` anidado.
- `GET /reports` (nuevo): lista paginada de reportes con prioridad y probabilidad — para el dashboard de gobierno.

---

#### `app/tasks.py` — Pipeline guarda en `procesamiento_ia`

**Antes:** El pipeline guardaba `priority`, `analysis`, `layers_summary` directamente en el modelo `Report`.

**Ahora:**

1. Actualiza `reporte.categoria` y `reporte.latitud/longitud` en `reportes`
2. Crea o actualiza un registro en `procesamiento_ia` con todos los resultados:
   - `tipo_problema` — derivado del texto con función `_tipo_problema()`
   - `probabilidad_atencion` — calculada por prioridad: alta→88%, media→62%, baja→30%
   - `contexto_urbano` — `layers_summary` serializado como JSON
3. Marca `reporte.estado = "ready"` al terminar

Nueva función `_tipo_problema(category, descripcion)`: clasifica el problema con más granularidad que la categoría Watson x (ej. dentro de "movilidad" distingue entre `"bache"`, `"accidente_vial"`, `"cruce_peatonal"`, `"señalamiento_vial"`).

---

#### `app/services/geocoder.py` — Adaptación al nuevo modelo

**Antes:** `_build_address()` usaba `report.street + report.ext_number + report.postal_code`.

**Ahora:** Usa `report.direccion_aprox + report.colonia + report.alcaldia`, que son los campos del nuevo modelo `Reporte`.

---

#### `app/services/layer_fetcher.py` — Corrección de error en startup

**Problema:** `load_all_layers()` lanzaba:
```
Assigning CRS to a GeoDataFrame without a geometry column is not supported.
```

**Causa:** En dos lugares se intentaba crear `gpd.GeoDataFrame(df, crs="EPSG:4326")` con DataFrames sin columna de geometría:
1. En `_csv_to_gdf()` cuando el CSV no tiene columnas `lat`/`lng`
2. En el bloque de carga de infracciones (CSV sin coordenadas)

**Solución:** Cuando un CSV no tiene columnas de coordenadas, se almacena como `pd.DataFrame` plano (no GeoDataFrame). Esto es correcto porque esos datos solo se usan para filtrado por atributo (columna `alcaldia`), no para análisis espacial.

```python
# Antes — causaba el error:
gdf = gpd.GeoDataFrame(df, crs="EPSG:4326")  # ❌ sin geometría

# Ahora — retorna DataFrame plano:
return df  # ✅ pd.DataFrame, sin CRS
```

El tipo de retorno de `_csv_to_gdf` pasó de `Optional[gpd.GeoDataFrame]` a `Union[gpd.GeoDataFrame, pd.DataFrame, None]`. El dict `_layers` usa el mismo tipo union.

---

#### `app/services/analysis/movilidad.py` — Compatibilidad con DataFrame plano

**Antes:** `_filter_by_alcaldia()` esperaba `Optional[gpd.GeoDataFrame]` y retornaba `gpd.GeoDataFrame`.

**Ahora:** Acepta `GeoDataFrame | DataFrame | None` y retorna `pd.DataFrame`. La lógica interna no cambia (solo hace `.str.upper().str.contains()`), pero el type hint y el manejo de vacío son correctos para ambos tipos.

---

### Resultado de `load_all_layers()` tras la corrección

```
atlas_de_riesgo_inundaciones.gpkg   →  4 908 registros  (GeoDataFrame)
niveles_de_inundacion.gpkg          →  2 362 registros  (GeoDataFrame)
tiraderos_clandestinos.gpkg         →  1 129 registros  (GeoDataFrame)
sistema_de_captacion_aguas_pluviales.gpkg → 10 265 registros (GeoDataFrame)
areas_verdes_cdmx.gpkg              → 11 739 registros  (GeoDataFrame)
CALLES.gpkg                         → 178 504 registros (GeoDataFrame)
hechos_transito.csv                 → 134 068 registros (GeoDataFrame con coords)
incidentes_c5.csv                   → 504 261 registros (GeoDataFrame con coords)
infracciones.csv                    →  83 689 registros (DataFrame plano)
```
