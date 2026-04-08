# Estructura inicial del proyecto — SeñalCDMX API

Este documento describe cada archivo generado en el setup inicial del backend, su propósito y cómo encaja en el flujo general del sistema.

---

## Contexto

SeñalCDMX es una API REST construida con FastAPI que:
1. Recibe un reporte ciudadano (texto + dirección)
2. Lo geocodifica si no viene con coordenadas
3. Lo clasifica con Watson x (Granite)
4. Hace análisis espacial contra capas de datos abiertos de la CDMX
5. Genera un reporte de prioridad con Watson x
6. Devuelve el resultado al frontend vía polling

Todo el procesamiento pesado ocurre en **background** para que el endpoint responda de inmediato al usuario.

---

## Archivos generados

### `app/config.py`

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    watsonx_api_key: str = ""
    ...
```

**Qué hace:** centraliza toda la configuración sensible (credenciales, URLs) en un solo objeto `settings` que se importa donde se necesite.

**Por qué importa:** usa `pydantic-settings`, que lee automáticamente las variables del archivo `.env` y las valida con tipos. Si falta `DATABASE_URL`, la app falla al arrancar con un mensaje claro — no en producción cuando ya se está usando. Esto evita el antipatrón de `os.getenv("X")` disperso por todo el código.

**Cómo se usa en el proyecto:**
- `database.py` lo importa para construir el engine de SQLAlchemy
- `services/classifier.py` y `services/report_gen.py` lo importarán para obtener las credenciales de Watson x
- `services/geocoder.py` lo usará para el `user_agent` de Nominatim

---

### `app/database.py`

```python
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(...)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Qué hace:** configura la conexión a PostgreSQL y expone tres cosas:
- `engine` — la conexión real a la base de datos
- `Base` — la clase base de la que heredan todos los modelos ORM
- `get_db()` — un generador que FastAPI usa como dependencia para inyectar sesiones de DB en cada request

**Por qué importa:** `get_db()` como dependencia de FastAPI garantiza que cada request tenga su propia sesión y que esa sesión se cierre correctamente aunque el endpoint lance una excepción. Sin esto, las conexiones se acumularían y la DB dejaría de responder bajo carga.

**Cómo se usa en el proyecto:** cada endpoint en `main.py` recibe `db: Session = Depends(get_db)` como parámetro. FastAPI maneja el ciclo de vida de la sesión automáticamente.

---

### `app/models.py`

```python
class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    status = Column(String(20), default="processing")
    description = Column(Text)
    ...
    location = Column(Geometry("POINT", srid=4326))  # PostGIS
    layers_summary = Column(JSONB)                   # PostgreSQL JSON binario
```

**Qué hace:** define la tabla `reports` en PostgreSQL usando SQLAlchemy ORM. Cada columna mapea a un campo del reporte ciudadano.

**Columnas clave y por qué están ahí:**

| Columna | Tipo | Propósito |
|---|---|---|
| `status` | `VARCHAR(20)` | Estado del pipeline: `processing` → `ready` / `error`. El frontend hace polling sobre este campo. |
| `lat`, `lng` | `FLOAT` | Coordenadas en WGS84. Pueden venir del usuario o del geocodificador. |
| `location` | `GEOMETRY(POINT, 4326)` | Punto PostGIS. Permite queries espaciales nativas en SQL (`ST_DWithin`, `ST_Contains`) si se necesitan en el futuro. |
| `category` | `VARCHAR(50)` | Resultado de la clasificación Watson x: `riesgos` / `movilidad` / `otro`. |
| `priority` | `VARCHAR(10)` | Resultado del análisis: `alta` / `media` / `baja`. |
| `layers_summary` | `JSONB` | Hallazgos del análisis espacial en formato JSON. JSONB (binario) permite indexado y queries sobre el JSON en PostgreSQL. |

**Por qué PostGIS:** aunque para el hackathon el análisis espacial principal ocurre en Python con GeoPandas, tener la columna `location` como tipo PostGIS deja la puerta abierta para queries espaciales directas en SQL (ej. "dame todos los reportes dentro de esta alcaldía") sin cambiar el esquema.

---

### `app/schemas.py`

```python
class ReportCreate(BaseModel): ...       # Entrada del POST /reports
class ReportCreatedResponse(BaseModel): ... # Respuesta inmediata: {report_id, status}
class ReportResponse(BaseModel): ...     # Respuesta del GET /reports/{id}
class LayersSummary(BaseModel): ...      # Estructura anidada dentro de ReportResponse
```

**Qué hace:** define los contratos de entrada y salida de la API usando Pydantic. Separa la representación de la API de la representación interna de la DB (los modelos ORM).

**Por qué importa esta separación:**
- El modelo ORM (`models.py`) refleja la estructura de la DB, que puede tener campos internos, columnas de auditoría, o tipos especiales (como `Geometry`) que no se deben exponer en la API.
- Los schemas de Pydantic validan y documentan automáticamente los tipos en `/docs` (Swagger UI).
- `ReportResponse` devuelve campos opcionales (`category`, `priority`, `analysis`) que son `None` mientras el status es `processing` — el frontend sabe que debe ignorarlos hasta que `status == "ready"`.

**Cómo funciona el flujo de tipos:**
```
Request JSON → ReportCreate (validación) → models.Report (DB) → ReportResponse (respuesta JSON)
```

---

### `app/main.py`

```python
app = FastAPI(title="SeñalCDMX API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], ...)

@app.post("/reports", status_code=202)
async def create_report(payload, background_tasks, db): ...

@app.get("/reports/{report_id}")
def get_report(report_id, db): ...
```

**Qué hace:** define la aplicación FastAPI con dos endpoints y configura CORS.

**`POST /reports` — flujo:**
1. Recibe y valida el body con `ReportCreate`
2. Crea el registro en DB con `status="processing"`
3. Registra `run_pipeline` como tarea en background
4. **Responde inmediatamente** con `{report_id, status: "processing"}` (HTTP 202)
5. El pipeline se ejecuta en paralelo sin bloquear la respuesta

Este diseño es crítico: Watson x puede tardar entre 30 segundos y 2 minutos. Si el endpoint esperara la respuesta completa, el frontend y el proxy HTTP agotarían su timeout.

**`GET /reports/{report_id}` — flujo:**
1. Busca el reporte en DB
2. Si `status == "processing"`, devuelve solo `{report_id, status}`
3. Si `status == "ready"`, devuelve el objeto completo con análisis, prioridad y hallazgos

**CORS:** habilitado solo para `localhost:3000` (el frontend Next.js en desarrollo). En producción se debería cambiar al dominio real.

---

### `app/tasks.py`

```python
async def run_pipeline(report_id: int, db: Session):
    # 1. Geocodificar (si no hay coordenadas)
    # 2. Clasificar con Watson x
    # 3. Cargar capas GeoJSON
    # 4. Análisis espacial (buffer 500m)
    # 5. Generar reporte con Watson x
    # 6. Guardar → status = "ready"
```

**Qué hace:** orquesta el pipeline completo de procesamiento. Es el "director" que llama a cada servicio en orden.

**Por qué es un archivo separado:** mantiene `main.py` limpio (solo routing) y permite testear el pipeline de forma independiente sin levantar el servidor HTTP.

**Manejo de errores:** si cualquier paso falla, el reporte queda con `status="error"` en la DB. El frontend puede detectar este estado y mostrar un mensaje apropiado en lugar de hacer polling indefinido.

**Imports lazy (dentro de la función):** los servicios se importan dentro de `run_pipeline` en lugar de al top del archivo. Esto evita errores de importación circular durante el arranque y permite que la app inicie aunque alguna dependencia de un servicio específico no esté disponible todavía.

---

### `docker-compose.yml`

```yaml
services:
  db:
    image: postgis/postgis:16-3.4
    ...
  app:
    build: .
    depends_on: [db]
    ...
```

**Qué hace:** define dos contenedores — la base de datos PostgreSQL+PostGIS y la aplicación FastAPI — con la red y volúmenes necesarios.

**Por qué `postgis/postgis` y no `postgres`:** la imagen oficial de Postgres no incluye la extensión PostGIS. `postgis/postgis:16-3.4` es la imagen oficial mantenida por el proyecto PostGIS, que ya tiene la extensión instalada y activada en la DB por defecto.

**Volumen `postgres_data`:** persiste los datos de la DB entre reinicios del contenedor. Sin esto, cada `docker-compose down` borraría todos los reportes.

**`depends_on: db`:** garantiza que el contenedor de la DB esté corriendo antes de que la app intente conectarse. (Nota: `depends_on` espera a que el contenedor *arranque*, no a que Postgres esté *listo para aceptar conexiones*. Para producción se usaría un healthcheck, pero para el hackathon es suficiente.)

---

### `requirements.txt`

| Paquete | Para qué |
|---|---|
| `fastapi` | Framework web |
| `uvicorn[standard]` | Servidor ASGI (corre FastAPI) |
| `sqlalchemy` | ORM para interactuar con PostgreSQL |
| `geoalchemy2` | Extiende SQLAlchemy con tipos PostGIS |
| `psycopg2-binary` | Driver Python-PostgreSQL |
| `pydantic` + `pydantic-settings` | Validación de datos y configuración |
| `geopandas` | Análisis espacial (buffer, intersecciones) |
| `shapely` | Geometrías (dependencia de GeoPandas) |
| `ibm-watsonx-ai` | SDK oficial de IBM para llamar a Watson x |
| `geopy` | Geocodificación vía Nominatim |

---

## Flujo completo del sistema (resumen visual)

```
Frontend (Next.js)
     │
     │  POST /reports {descripción + dirección}
     ▼
main.py ──→ crea Report(status="processing") en DB
     │      lanza run_pipeline() en background
     │
     │  Responde: {report_id: 1, status: "processing"}  ← inmediato
     ▼
Frontend hace polling GET /reports/1 cada 5 segundos

Mientras tanto, en background:
tasks.run_pipeline()
     ├── geocoder.py    → dirección → (lat, lng)
     ├── classifier.py  → descripción → "riesgos" / "movilidad"
     ├── layer_fetcher.py → carga GeoJSON de CDMX desde data/layers/
     ├── spatial.py     → buffer 500m → findings
     └── report_gen.py  → Watson x → análisis + prioridad
          │
          └── DB: Report(status="ready", analysis=..., priority=...)

Frontend recibe GET /reports/1 → {status: "ready", analysis: "...", priority: "alta"}
```

---

## Qué falta implementar

Los servicios en `app/services/` existen como módulos vacíos. Son el siguiente paso:

1. **`geocoder.py`** — llamada a Nominatim con la dirección completa
2. **`classifier.py`** — llamada a Watson x con `CLASSIFICATION_PROMPT`
3. **`layer_fetcher.py`** — carga de GeoJSON desde `data/layers/` (o descarga al inicio)
4. **`spatial.py`** — análisis con GeoPandas: buffer 500m, `sjoin`, conteo de features
5. **`report_gen.py`** — llamada a Watson x con `REPORT_PROMPT` y parseo de prioridad
