# SeñalCDMX — Backend API

Proyecto para el hackathon IBM Watsonx Challenge en Talent Land 2025, track **Ciudades Resilientes**.

Sistema que recibe reportes ciudadanos (texto o audio), los geocodifica, los clasifica con Watson x, los analiza contra capas de datos abiertos de la CDMX, y genera un reporte de análisis con prioridad asignada por IA — todo en menos de 3 minutos.

---

## Stack

- **Framework:** FastAPI
- **Base de datos:** PostgreSQL con extensión PostGIS (geometrías espaciales)
- **ORM:** SQLAlchemy + GeoAlchemy2
- **Análisis espacial:** GeoPandas, Shapely
- **IA / clasificación:** IBM Watson x (modelo Granite)
- **Geocodificación:** Nominatim (OpenStreetMap) — sin costo
- **Cola de tareas:** FastAPI BackgroundTasks (suficiente para hackathon)
- **Contenedores:** Docker Compose (PostgreSQL+PostGIS, app)
- **Frontend:** Next.js — desarrollado por otro integrante del equipo, consume esta API

---

## Estructura del proyecto

```
señalcdmx-api/
├── app/
│   ├── main.py              # FastAPI app, rutas, CORS
│   ├── models.py            # SQLAlchemy models + PostGIS
│   ├── schemas.py           # Pydantic schemas (request/response)
│   ├── database.py          # Engine, SessionLocal, get_db
│   ├── config.py            # Settings desde variables de entorno
│   ├── services/
│   │   ├── geocoder.py      # Dirección → (lat, lng) via Nominatim
│   │   │                    # También geocodifica registros de capas sin coords
│   │   ├── classifier.py    # Descripción → "riesgos" | "movilidad" via Watson x
│   │   ├── layer_fetcher.py # Carga capas al arrancar el servidor desde data/layers/
│   │   ├── spatial.py       # Buffer 500m, sjoin, intersecciones — orquesta ambas categorías
│   │   ├── analysis/
│   │   │   ├── riesgos.py   # Lógica de análisis para gestión de riesgos
│   │   │   └── movilidad.py # Lógica de análisis para movilidad e infraestructura
│   │   └── report_gen.py    # Recibe métricas + interpretación manual → Watson x → conclusión
│   └── tasks.py             # Pipeline async orquestado con BackgroundTasks
├── data/
│   └── layers/
│       ├── riesgos/         # Capas GeoJSON/GeoPackage para gestión de riesgos
│       │   ├── atlas_inundaciones.geojson
│       │   ├── niveles_inundacion.geojson
│       │   ├── presas.geojson
│       │   ├── captacion_pluvial.geojson
│       │   ├── tiraderos_clandestinos.geojson
│       │   └── areas_verdes.geojson
│       └── movilidad/       # Capas para movilidad e infraestructura
│           ├── CALLES.gpkg  # Red vial — fuente de intersecciones
│           ├── infracciones.geojson
│           ├── hechos_transito.geojson
│           └── incidentes_viales_c5.geojson
├── requirements.txt
├── .env.example
└── docker-compose.yml
```

---

## Endpoints

### `POST /reports`
Recibe el reporte del usuario. Guarda en DB y dispara el pipeline en background.
Responde **inmediatamente** con `report_id` y `status: "processing"`.

**Request body:**
```json
{
  "description": "string (texto libre o transcripción de audio)",
  "street": "string",
  "ext_number": "string",
  "int_number": "string | null",
  "postal_code": "string",
  "alcaldia": "string",
  "colonia": "string",
  "between_street_1": "string | null",
  "between_street_2": "string | null",
  "lat": "float | null",
  "lng": "float | null"
}
```

**Response:**
```json
{
  "report_id": "integer",
  "status": "processing"
}
```

---

### `GET /reports/{report_id}`
El frontend hace polling cada 5 segundos hasta que `status` sea `"ready"`.

**Response (procesando):**
```json
{
  "report_id": 1,
  "status": "processing"
}
```

**Response (listo):**
```json
{
  "report_id": 1,
  "status": "ready",
  "category": "riesgos | movilidad",
  "priority": "alta | media | baja",
  "lat": 19.432,
  "lng": -99.133,
  "analysis": "string — reporte generado por Watson x",
  "layers_summary": {
    "matched_layers": ["Atlas de riesgo - Inundaciones", "Tiraderos clandestinos"],
    "findings": ["El punto se encuentra en zona de riesgo alto de inundación", "..."]
  },
  "created_at": "ISO 8601"
}
```

---

## Pipeline async (`tasks.py`)

```python
async def run_pipeline(report_id: int, db: Session):
    report = get_report(db, report_id)

    # 1. Geocodificar si el usuario no puso marcador en el mapa
    if not report.lat:
        report.lat, report.lng = await geocode_address(report)
        db.commit()

    # 2. Watson x clasifica la descripción del reporte
    category = await classify(report.description)
    # Valores posibles: "riesgos" | "movilidad"

    # 3. Cargar capas correspondientes a la categoría desde data/layers/
    layers = layer_fetcher.get_layers(category)

    # 4. Ejecutar análisis espacial según categoría
    if category == "riesgos":
        metrics, maps = await analyze_riesgos(report.lat, report.lng, layers)
    elif category == "movilidad":
        metrics, maps = await analyze_movilidad(report.lat, report.lng, layers)

    # 5. En este prototipo la interpretación de métricas y mapas es MANUAL.
    #    El objeto `metrics` y las imágenes `maps` se guardan en DB/disco
    #    para que puedan ser revisados. La interpretación escrita se pasa
    #    como input al siguiente paso.
    #    TODO post-hackathon: reemplazar con interpretación automática por IA.

    # 6. Watson x recibe las métricas + interpretación manual y genera:
    #       - conclusión narrativa
    #       - prioridad: "alta" | "media" | "baja"
    #       - propuestas de acción
    result = await generate_report(report, metrics, interpretation=None)

    # 7. Guardar resultado completo y marcar reporte como listo
    update_report(db, report_id,
                  category=category,
                  metrics=metrics,
                  maps=maps,
                  conclusion=result.conclusion,
                  priority=result.priority,
                  actions=result.actions,
                  status="ready")
```

---

## Categorías de análisis (hackathon: solo estas dos)

### A. Gestión de riesgos — inundaciones (`services/analysis/riesgos.py`)

**Capas** (archivos en `data/layers/riesgos/`):
| Archivo | Descripción |
|---|---|
| `atlas_inundaciones.geojson` | Zonas con riesgo de inundación |
| `niveles_inundacion.geojson` | Niveles de inundación y carencia de áreas verdes |
| `presas.geojson` | Ubicación de presas |
| `captacion_pluvial.geojson` | Sistema de captación de aguas pluviales |
| `tiraderos_clandestinos.geojson` | Tiraderos clandestinos |
| `areas_verdes.geojson` | Inventario de áreas verdes |

**Procedimiento:**

1. Crear buffer de 500 metros en EPSG:32614 (UTM zona 14N) alrededor del punto del reporte. Reconvertir a EPSG:4326 para los joins.
2. Para cada capa, verificar si los registros tienen geometría/coordenadas. Si no, llamar a `geocoder.geocode_records(gdf)` para obtenerlas antes del filtrado.
3. Filtrar cada capa con `geopandas.sjoin` o `.within(buffer)` para quedarse solo con los registros dentro del buffer.
4. Calcular y devolver las siguientes métricas:

```python
metrics = {
    "zona_riesgo_inundacion": bool,         # ¿el punto cae en zona de riesgo?
    "nivel_riesgo": "alto | medio | bajo | ninguno",
    "n_presas_cercanas": int,
    "n_puntos_captacion": int,
    "n_tiraderos": int,
    "cobertura_areas_verdes_m2": float,     # suma de área verde dentro del buffer
    "deficit_areas_verdes": bool,           # según capa de carencia
}
```

5. Generar un mapa PNG por cada capa con registros encontrados, usando `matplotlib` + `contextily` (mapa base de CDMX). Guardar en `data/maps/{report_id}/`.

---

### B. Movilidad e infraestructura — cruces peatonales (`services/analysis/movilidad.py`)

**Capas** (archivos en `data/layers/movilidad/`):
| Archivo | Descripción |
|---|---|
| `CALLES.gpkg` | Red vial — fuente para detectar intersecciones |
| `infracciones.geojson` | Infracciones al reglamento de tránsito |
| `hechos_transito.geojson` | Hechos de tránsito (accidentes) |
| `incidentes_viales_c5.geojson` | Incidentes viales reportados por C5 |

**Procedimiento:**

1. Crear buffer de 500 metros (EPSG:32614 → EPSG:4326) alrededor del punto del reporte.
2. Para cada capa, verificar si los registros tienen geometría. Si no, llamar a `geocoder.geocode_records(gdf)`.
3. Detectar intersecciones dentro del buffer usando `CALLES.gpkg`:
   - Encontrar nodos donde se cruzan dos o más segmentos de calle.
   - Asignar un identificador único a cada intersección (`intersection_id`).
   - Asociar los eventos de las otras capas al `intersection_id` más cercano.
4. Filtrar infracciones, hechos de tránsito e incidentes dentro del buffer.
5. Calcular y devolver las siguientes métricas:

```python
metrics = {
    "n_intersecciones": int,               # total de intersecciones en el buffer
    "interseccion_mas_conflictiva": str,   # intersection_id con más eventos
    "n_infracciones": int,
    "n_hechos_transito": int,
    "n_incidentes_c5": int,
    "total_eventos": int,                  # suma de los tres anteriores
    "eventos_por_interseccion": dict,      # {intersection_id: n_eventos}
}
```

6. Generar un mapa PNG con:
   - Red vial dentro del buffer.
   - Intersecciones marcadas (tamaño proporcional a número de eventos).
   - Capas de hechos e incidentes superpuestas con colores distintos.
   - Guardar en `data/maps/{report_id}/`.

---

### Geocodificación de registros sin coordenadas (`geocoder.py`)

Algunas capas pueden tener columnas de dirección pero no geometría. La función `geocode_records(gdf)` debe:

```python
def geocode_records(gdf: gpd.GeoDataFrame, address_col: str) -> gpd.GeoDataFrame:
    """
    Para cada fila sin geometría, construye una dirección a partir de address_col
    y consulta Nominatim para obtener lat/lng.
    Devuelve el GeoDataFrame con geometrías completas.
    Usa caché para no repetir consultas idénticas.
    """
```

Usar `geopy.geocoders.Nominatim` con `user_agent` desde config. Agregar delay de 1 segundo entre requests para respetar el rate limit de Nominatim.

---

## Generación de reporte con Watson x (`report_gen.py`)

Watson x recibe las métricas calculadas más una interpretación manual (en este prototipo) y devuelve conclusión, prioridad y propuestas de acción.

```python
REPORT_PROMPT = """
Eres un analista de riesgo urbano para la Ciudad de México.
Con base en el reporte ciudadano y las métricas de análisis geoespacial,
genera una respuesta estructurada en JSON con exactamente estos campos:

{{
  "conclusion": "párrafo de 2-3 oraciones explicando la situación",
  "priority": "alta | media | baja",
  "priority_justification": "una oración justificando la prioridad",
  "proposed_actions": ["acción 1", "acción 2", "acción 3"]
}}

Responde SOLO con el JSON, sin texto adicional.

Reporte ciudadano: {description}
Categoría: {category}
Ubicación: {colonia}, {alcaldia}
Métricas del análisis: {metrics}
Interpretación del analista: {interpretation}
"""
```

Parsear la respuesta como JSON. Si el parsing falla, reintentar una vez con un prompt más estricto.

---

## Response final del endpoint `GET /reports/{report_id}`

```json
{
  "report_id": 1,
  "status": "ready",
  "category": "riesgos | movilidad",
  "priority": "alta | media | baja",
  "priority_justification": "string",
  "lat": 19.432,
  "lng": -99.133,
  "conclusion": "string — conclusión generada por Watson x",
  "proposed_actions": ["acción 1", "acción 2", "acción 3"],
  "metrics": { },
  "maps": [
    { "layer": "atlas_inundaciones", "url": "/static/maps/1/atlas_inundaciones.png" },
    { "layer": "tiraderos", "url": "/static/maps/1/tiraderos.png" }
  ],
  "created_at": "ISO 8601"
}
```

Los mapas se sirven como archivos estáticos con `app.mount("/static", StaticFiles(directory="data"), name="static")`.

---

## Clasificación con Watson x (`classifier.py`)

Zero-shot classification con modelo Granite. Devuelve solo la categoría como string.

```python
CLASSIFICATION_PROMPT = """
Eres un clasificador de reportes ciudadanos para la Ciudad de México.
Clasifica el siguiente reporte en UNA de estas dos categorías:
- riesgos: inundaciones, encharcamientos, drenaje tapado, zonas de peligro por agua, tiraderos
- movilidad: accidentes viales, infracciones, cruces peatonales peligrosos, baches, semáforos

Responde SOLO con la palabra: riesgos   o   movilidad

Reporte: {description}
"""
```

Si la respuesta no es exactamente `"riesgos"` o `"movilidad"`, hacer un segundo intento. Si falla de nuevo, asignar `"riesgos"` como fallback y loggear la advertencia.

---

## Notas de desarrollo

```env
DATABASE_URL=postgresql://user:password@localhost:5432/señalcdmx
WATSONX_API_KEY=
WATSONX_PROJECT_ID=
WATSONX_URL=https://us-south.ml.cloud.ibm.com
NOMINATIM_USER_AGENT=señalcdmx-hackathon
```

---

## Notas de desarrollo

- Las capas se cargan **una sola vez al arrancar el servidor** (`layer_fetcher.py` con `@app.on_event("startup")`). No hacer I/O de archivos por cada reporte.
- CRS de trabajo: leer capas en **EPSG:4326**, reproyectar a **EPSG:32614** (UTM zona 14N) solo para calcular el buffer en metros, luego volver a 4326 para los joins y los mapas.
- Los mapas PNG se generan con `matplotlib` + `contextily` (tiles de OpenStreetMap). Guardar en `data/maps/{report_id}/` y servir como estáticos.
- CORS habilitado para `localhost:3000` (Next.js dev).
- El frontend hace polling a `GET /reports/{id}` cada 5 segundos. No usar WebSockets por ahora.
- La interpretación manual de métricas es un placeholder en este prototipo. El campo `interpretation` en `report_gen.py` puede ser `None` o una cadena vacía — Watson x genera la conclusión con solo las métricas.
- Para la demo: preparar 2 reportes de prueba con coords reales de CDMX, uno por categoría (ej. zona de inundación en Iztapalapa para riesgos; cruce Insurgentes-Álvaro Obregón para movilidad).
- Nominatim tiene rate limit de 1 req/seg — agregar `time.sleep(1)` entre geocodificaciones de registros.

---

## Variables de entorno (`.env`)

```env
DATABASE_URL=postgresql://user:password@localhost:5432/señalcdmx
WATSONX_API_KEY=
WATSONX_PROJECT_ID=
WATSONX_URL=https://us-south.ml.cloud.ibm.com
NOMINATIM_USER_AGENT=señalcdmx-hackathon
MAPS_OUTPUT_DIR=data/maps
LAYERS_DIR=data/layers
```

---

---

## Comandos útiles

```bash
# Levantar base de datos
docker-compose up -d

# Instalar dependencias
pip install -r requirements.txt

# Correr servidor en desarrollo
uvicorn app.main:app --reload --port 8000

# Ver documentación automática de la API
# http://localhost:8000/docs
```