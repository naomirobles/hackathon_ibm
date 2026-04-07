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
│   │   ├── classifier.py    # Descripción → categoría via Watson x
│   │   ├── layer_fetcher.py # Carga capas GeoJSON de datos abiertos CDMX
│   │   ├── spatial.py       # Análisis espacial GeoPandas (buffer 500m)
│   │   └── report_gen.py    # Genera reporte final con Watson x
│   └── tasks.py             # Pipeline async orquestado con BackgroundTasks
├── data/
│   └── layers/              # GeoJSON de capas CDMX descargados al inicio
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

    # 1. Geocodificar si el usuario no puso marcador
    if not report.lat:
        report.lat, report.lng = await geocode(report)
        db.commit()

    # 2. Clasificar descripción con Watson x
    category = await classify(report.description)
    # Valores posibles: "riesgos" | "movilidad" | "otro"

    # 3. Cargar capas relevantes según categoría
    layers_gdf = fetch_layers(category)

    # 4. Análisis espacial: buffer 500m alrededor del punto
    findings = spatial_analysis(report.lat, report.lng, layers_gdf)

    # 5. Generar reporte con Watson x
    analysis_text, priority = await generate_report(report, findings)

    # 6. Guardar y marcar como listo
    update_report(db, report_id, category, analysis_text, priority, status="ready")
```

---

## Categorías de análisis (hackathon: solo estas dos)

### A. Gestión de riesgos — inundaciones

Capas a usar (GeoJSON del portal datos abiertos CDMX):
- Atlas de riesgo — niveles de inundación
- Presas
- Sistema de captación de aguas pluviales
- Tiraderos clandestinos
- Inventario de áreas verdes
- Datos climáticos de la zona

Lógica espacial: si el punto del reporte cae dentro o a menos de 500m de zonas de riesgo, reportar nivel de exposición.

### B. Movilidad e infraestructura — seguridad en cruces peatonales

Capas a usar:
- Red vial (para ubicar intersecciones cercanas)
- Registro de infracciones
- Hechos de tránsito
- Incidentes viales reportados por ciudadanos

Lógica espacial: contar incidentes y hechos de tránsito en radio de 500m, identificar intersecciones de alto riesgo.

---

## Clasificación con Watson x (`classifier.py`)

Usar zero-shot classification con modelo Granite. El prompt debe devolver únicamente la categoría.

```python
CLASSIFICATION_PROMPT = """
Eres un clasificador de reportes ciudadanos para la Ciudad de México.
Clasifica el siguiente reporte en UNA de estas categorías:
- riesgos: inundaciones, encharcamientos, drenaje, zonas de peligro natural
- movilidad: accidentes viales, infracciones, cruces peligrosos, baches
- otro: cualquier otra cosa

Responde SOLO con la categoría en minúsculas, sin explicación.

Reporte: {description}
"""
```

---

## Generación de reporte con Watson x (`report_gen.py`)

```python
REPORT_PROMPT = """
Eres un analista de seguridad urbana de la Ciudad de México.
Con base en el siguiente reporte ciudadano y los datos geoespaciales del entorno,
genera un análisis breve con:
1. Resumen del problema reportado
2. Hallazgos relevantes del entorno (datos geoespaciales)
3. Prioridad de atención: alta, media o baja — con justificación

Sé conciso. Máximo 200 palabras.

Reporte: {description}
Categoría: {category}
Ubicación: {alcaldia}, {colonia}
Hallazgos geoespaciales: {findings}
"""
```

La respuesta debe ser parseada para extraer la prioridad (`alta | media | baja`) y el texto de análisis.

---

## Variables de entorno (`.env`)

```env
DATABASE_URL=postgresql://user:password@localhost:5432/señalcdmx
WATSONX_API_KEY=
WATSONX_PROJECT_ID=
WATSONX_URL=https://us-south.ml.cloud.ibm.com
NOMINATIM_USER_AGENT=señalcdmx-hackathon
```

---

## Notas de desarrollo

- Las capas GeoJSON de datos abiertos CDMX se descargan **una sola vez al arrancar el servidor** y se guardan en `data/layers/`. No hacer requests al portal por cada reporte — sería demasiado lento.
- El análisis espacial usa `geopandas.sjoin` o `buffer()` de Shapely. El CRS de trabajo es **EPSG:4326** (WGS84) para coords, convertir a **EPSG:32614** (UTM zona 14N) para calcular distancias en metros.
- CORS habilitado para `localhost:3000` (Next.js en desarrollo).
- El frontend hace polling a `GET /reports/{id}` cada 5 segundos. No implementar WebSockets por ahora.
- Watson x tiene latencia variable — el pipeline puede tardar entre 30 segundos y 2 minutos dependiendo de la carga. El tiempo objetivo visible al usuario es de 1 a 3 minutos.
- Para demo del hackathon: preparar al menos 2 casos de prueba con direcciones reales de CDMX, uno por categoría (ej. zona de inundación en Iztapalapa, cruce conflictivo en Cuauhtémoc).

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