# SeñalCDMX API — Documentación de arquitectura y flujo

## Qué hace este proyecto

SeñalCDMX es una API REST que recibe reportes ciudadanos sobre problemas urbanos en la Ciudad de México (inundaciones, accidentes viales, cruces peligrosos, etc.), los analiza automáticamente con datos geoespaciales abiertos y con IBM Watson x, y produce un reporte con prioridad de atención asignada por IA.

El flujo completo ocurre en segundo plano — el usuario recibe una respuesta inmediata con un `report_id` y hace polling cada pocos segundos hasta que el análisis esté listo.

---

## Estructura del proyecto y por qué está así

```
senialcdmx-api/
├── app/
│   ├── main.py              ← Punto de entrada HTTP. Define rutas y middleware.
│   ├── models.py            ← Esquema de la base de datos (tabla `reports`).
│   ├── schemas.py           ← Validación de requests y forma de responses (Pydantic).
│   ├── database.py          ← Conexión a PostgreSQL y sesión de SQLAlchemy.
│   ├── config.py            ← Variables de entorno (.env) centralizadas.
│   ├── tasks.py             ← Pipeline completo del análisis en background.
│   └── services/
│       ├── geocoder.py      ← Dirección → (lat, lng) via Nominatim.
│       ├── classifier.py    ← Descripción → categoría via Watson x Granite.
│       ├── layer_fetcher.py ← Carga capas GeoPackage/CSV una sola vez al arrancar.
│       ├── spatial.py       ← Orquestador: elige análisis según categoría.
│       ├── report_gen.py    ← Genera reporte narrativo + prioridad con Watson x.
│       └── analysis/
│           ├── riesgos.py   ← Lógica espacial para inundaciones y riesgos.
│           └── movilidad.py ← Lógica espacial para accidentes e infraestructura.
├── data/
│   └── layers/              ← Archivos GeoPackage y CSV de datos abiertos CDMX.
├── requirements.txt
├── docker-compose.yml       ← PostgreSQL+PostGIS + contenedor de la app.
└── .env.example
```

**Por qué esta separación:**

- `main.py` solo conoce HTTP — no sabe nada de análisis espacial ni de Watson x.
- `tasks.py` orquesta el pipeline completo pero no implementa ningún paso directamente — delega en los servicios.
- Cada servicio tiene una única responsabilidad. Si se cambia el proveedor de geocodificación, solo se toca `geocoder.py`. Si se cambia el modelo de Watson x, solo se toca `classifier.py` o `report_gen.py`.
- Las capas geoespaciales (`layer_fetcher.py`) se cargan **una sola vez al arrancar** el servidor y quedan en memoria. Leerlas por cada reporte sería demasiado lento para el tiempo objetivo de 1-3 minutos.
- `analysis/riesgos.py` y `analysis/movilidad.py` están separados porque tienen lógica de dominio muy diferente (métricas distintas, capas distintas, reglas de prioridad distintas).

---

## Archivo principal: `app/main.py`

`main.py` es el punto de entrada de la aplicación FastAPI. Todo request HTTP entra aquí.

### Qué hace al arrancar

```
uvicorn app.main:app --reload --port 8000
       │        │
       │        └─ objeto FastAPI en app/main.py
       └─ módulo app/main.py
```

Al arrancar, FastAPI ejecuta el evento `startup`:

```python
@app.on_event("startup")
async def startup_event():
    from app.services.layer_fetcher import load_all_layers
    load_all_layers()   # Lee todos los .gpkg y .csv a memoria RAM
```

Esto puede tardar 10-30 segundos dependiendo del tamaño de los archivos — es intencional y solo ocurre una vez.

### Rutas que expone

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/reports` | Recibe un reporte ciudadano, lo guarda en DB, dispara el pipeline en background. Responde **inmediatamente** con `report_id`. |
| `GET` | `/reports/{report_id}` | Devuelve el estado del reporte. El frontend hace polling aquí cada 5 segundos. |

### Qué llama `main.py`

```
main.py
├── app.models          → para crear el objeto Report en DB
├── app.schemas         → para validar el body del request y serializar la response
├── app.database        → para obtener la sesión de DB (get_db)
└── app.tasks           → run_pipeline(report_id, db) — corre en background
```

---

## Flujo completo de un reporte

```
Cliente HTTP
    │
    │  POST /reports  { description, street, alcaldia, ... }
    ▼
main.py — create_report()
    │  1. Valida body con schemas.ReportCreate
    │  2. Guarda Report en PostgreSQL (status="processing")
    │  3. Dispara run_pipeline() en BackgroundTasks
    │  4. Responde { report_id: 42, status: "processing" }  ← inmediato
    ▼
tasks.py — run_pipeline(report_id=42, db)        [corre en segundo plano]
    │
    │  Paso 1 — Geocodificación (si no hay coords)
    ├─→ services/geocoder.py
    │       geocode(report)
    │       Construye dirección → llama a Nominatim (OpenStreetMap)
    │       Retorna (lat, lng) → guarda en DB
    │
    │  Paso 2 — Clasificación con Watson x
    ├─→ services/classifier.py
    │       classify(description)
    │       Envía prompt a IBM Granite → respuesta: "riesgos" | "movilidad" | "otro"
    │       Fallback: clasificación por palabras clave si no hay API key
    │
    │  Paso 3 — Cargar capas de la categoría
    ├─→ services/layer_fetcher.py
    │       get_layers("riesgos")  o  get_layers("movilidad")
    │       Retorna dict de GeoDataFrames ya cargados en memoria
    │
    │  Paso 4 — Análisis espacial
    ├─→ services/spatial.py
    │       spatial_analysis(lat, lng, category, layers, alcaldia)
    │       │
    │       ├─→ analysis/riesgos.py   (si category == "riesgos")
    │       │       - Buffer 500m en EPSG:32614 (UTM 14N)
    │       │       - sjoin con atlas de inundaciones, tiraderos, captación pluvial, áreas verdes
    │       │       - Retorna: { zona_riesgo_inundacion, nivel_riesgo, n_tiraderos, ... }
    │       │
    │       └─→ analysis/movilidad.py (si category == "movilidad")
    │               - Buffer 500m
    │               - sjoin con hechos de tránsito e incidentes C5 (tienen coords)
    │               - Filtro por alcaldía para infracciones (sin coords)
    │               - Retorna: { n_hechos_transito, n_incidentes_c5, intersecciones_riesgo, ... }
    │
    │  Paso 5 — Generación de reporte con Watson x
    ├─→ services/report_gen.py
    │       generate_report(report, metrics, layers_summary, category)
    │       Arma prompt con: descripción + categoría + alcaldía/colonia + hallazgos
    │       Llama a IBM Granite → texto narrativo (máx. 200 palabras)
    │       Extrae prioridad del texto: "alta" | "media" | "baja"
    │       Fallback: prioridad por reglas si no hay API key
    │
    │  Paso 6 — Guardar resultado
    └─→ DB: report.status = "ready"
             report.category, priority, analysis, layers_summary
```

### Mientras tanto, el frontend hace polling:

```
GET /reports/42
→ { report_id: 42, status: "processing" }   ← durante el análisis
→ { report_id: 42, status: "processing" }
→ { report_id: 42, status: "ready",
    category: "riesgos",
    priority: "alta",
    lat: 19.432, lng: -99.133,
    analysis: "El reporte se ubica en zona de alto riesgo de inundación...",
    layers_summary: {
      matched_layers: ["Atlas de Riesgo — Inundaciones", "Tiraderos Clandestinos"],
      findings: ["El punto se encuentra en zona de riesgo alto...", "..."]
    }
  }
```

---

## Cómo probar la API REST

### 0. Levantar el entorno

```bash
# Copiar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de Watson x (opcional para pruebas locales)

# Levantar PostgreSQL+PostGIS
docker-compose up -d db

# Instalar dependencias
pip install -r requirements.txt

# Correr el servidor
uvicorn app.main:app --reload --port 8000
```

La documentación interactiva estará en: `http://localhost:8000/docs`

---

### 1. Crear un reporte — caso riesgos (inundación en Iztapalapa)

```bash
curl -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Hay un encharcamiento enorme que no baja desde ayer, el agua llega a la rodilla y hay basura flotando. El drenaje está tapado.",
    "street": "Av. Ermita Iztapalapa",
    "ext_number": "1500",
    "postal_code": "09810",
    "alcaldia": "Iztapalapa",
    "colonia": "Barrio San Miguel"
  }'
```

**Respuesta esperada:**
```json
{
  "report_id": 1,
  "status": "processing"
}
```

---

### 2. Crear un reporte — caso movilidad (cruce peligroso en Cuauhtémoc)

```bash
curl -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -d '{
    "description": "En la esquina de Insurgentes con Reforma hay muchos accidentes, los peatones no tienen tiempo de cruzar y los coches no respetan el semáforo.",
    "street": "Paseo de la Reforma",
    "ext_number": "250",
    "postal_code": "06600",
    "alcaldia": "Cuauhtémoc",
    "colonia": "Juárez",
    "between_street_1": "Insurgentes",
    "lat": 19.4284,
    "lng": -99.1677
  }'
```

---

### 3. Consultar el estado (polling)

```bash
curl http://localhost:8000/reports/1
```

**Respuesta mientras procesa:**
```json
{
  "report_id": 1,
  "status": "processing"
}
```

**Respuesta cuando termina:**
```json
{
  "report_id": 1,
  "status": "ready",
  "category": "riesgos",
  "priority": "alta",
  "lat": 19.3724,
  "lng": -99.0633,
  "analysis": "El punto reportado se ubica dentro de una zona catalogada con riesgo alto de inundación según el Atlas de Riesgo de la CDMX...",
  "layers_summary": {
    "matched_layers": ["Atlas de Riesgo — Inundaciones", "Tiraderos Clandestinos"],
    "findings": [
      "El punto se encuentra en zona de riesgo de inundación (nivel: alto).",
      "Se detectaron 3 tiradero(s) clandestino(s) en un radio de 500 m."
    ]
  },
  "created_at": "2025-04-08T18:30:00"
}
```

---

### 4. Probar con coordenadas explícitas (sin geocodificación)

Si el frontend envía las coordenadas del pin en el mapa, el servidor se salta el paso de Nominatim:

```bash
curl -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Bache enorme que ya dañó varias llantas",
    "street": "Eje Central Lázaro Cárdenas",
    "ext_number": "100",
    "postal_code": "06050",
    "alcaldia": "Cuauhtémoc",
    "colonia": "Centro Histórico",
    "lat": 19.4326,
    "lng": -99.1332
  }'
```

---

### 5. Verificar que los campos son requeridos

```bash
# Sin descripción → 422 Unprocessable Entity
curl -X POST http://localhost:8000/reports \
  -H "Content-Type: application/json" \
  -d '{
    "street": "Calle sin descripción",
    "ext_number": "1",
    "postal_code": "06000",
    "alcaldia": "Cuauhtémoc",
    "colonia": "Centro"
  }'
```

---

### 6. Reporte inexistente → 404

```bash
curl http://localhost:8000/reports/9999
# { "detail": "Reporte no encontrado" }
```

---

### 7. Documentación interactiva (Swagger UI)

Abre en el navegador:

```
http://localhost:8000/docs
```

Desde ahí puedes ejecutar todos los endpoints sin necesidad de curl, ver los schemas de request/response y explorar los campos opcionales.

---

## Comportamiento sin Watson x

Si `WATSONX_API_KEY` está vacío en `.env`, el sistema funciona con fallbacks:

| Paso | Comportamiento |
|------|----------------|
| Clasificación | Palabras clave en el texto (ej. "inundación" → "riesgos") |
| Reporte final | Texto generado con las métricas directamente, sin narrativa IA |
| Prioridad | Reglas simples sobre las métricas (ej. `nivel_riesgo == "alto"` → `"alta"`) |

Esto permite desarrollar y probar el pipeline completo sin necesitar credenciales de IBM.

---

## Variables de entorno requeridas

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `DATABASE_URL` | `postgresql://user:pass@host:5432/db` | Sí |
| `WATSONX_API_KEY` | API key de IBM Cloud | Solo para IA real |
| `WATSONX_PROJECT_ID` | ID del proyecto en Watson x | Solo para IA real |
| `WATSONX_URL` | URL del servicio Watson x | Solo para IA real |
| `NOMINATIM_USER_AGENT` | Identificador para Nominatim (cualquier string) | Sí |
