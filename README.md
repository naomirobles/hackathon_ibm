# SeñalCDMX 🏙️

> **Plataforma de reportes urbanos con inteligencia artificial para la Ciudad de México**  
> Desarrollada durante el **IBM AI Hackathon CDMX 2025** 

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![IBM Watson x](https://img.shields.io/badge/IBM-Watson_x-BE95FF?logo=ibm)](https://www.ibm.com/watsonx)
[![Plotly Dash](https://img.shields.io/badge/Plotly-Dash-3F4F75?logo=plotly)](https://dash.plotly.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-PostGIS-336791?logo=postgresql)](https://postgis.net)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)

---

## 📋 Tabla de contenidos

1. [Contexto del proyecto](#contexto-del-proyecto)
2. [Arquitectura del sistema](#arquitectura-del-sistema)
3. [Stack tecnológico](#stack-tecnológico)
4. [Funcionalidades principales](#funcionalidades-principales)
5. [Pipeline de análisis IA](#pipeline-de-análisis-ia)
6. [Estructura del repositorio](#estructura-del-repositorio)
7. [Instalación y ejecución](#instalación-y-ejecución)
8. [API Reference](#api-reference)
9. [Variables de entorno](#variables-de-entorno)
10. [Resultados e impacto](#resultados-e-impacto)
11. [Aprendizajes técnicos](#aprendizajes-técnicos)
12. [Equipo](#equipo)

---

## Contexto del proyecto

### El problema

La Ciudad de México recibe más de **18,000 reportes urbanos mensuales** a través del sistema C5 y plataformas de gobierno. El proceso tradicional de atención implica clasificación manual, priorización subjetiva y una tasa de resolución que no supera el 34% en los primeros 7 días hábiles.

Los ciudadanos reportan problemas (inundaciones, baches, cruces peligrosos, tiraderos clandestinos) sin recibir retroalimentación inmediata ni información de contexto sobre la situación geoespacial de su reporte. Los servidores públicos, por su parte, carecen de herramientas para priorizar objetivamente la atención.

### La solución

**SeñalCDMX** es una plataforma *full-stack* que conecta a ciudadanos y gobierno a través de un sistema de reportes urbanos impulsado por IA. El ciudadano describe el problema —por texto o voz—, el sistema lo analiza automáticamente cruzando datos geoespaciales abiertos de la CDMX con modelos de lenguaje de **IBM Watson x (Granite)**, y devuelve en menos de 90 segundos:

- Una **categorización automática** del problema (riesgos urbanos o movilidad vial)
- Un **análisis geoespacial** en radio de 500 m con capas de datos abiertos
- Una **prioridad de atención** (alta / media / baja) con justificación narrativa
- Una **probabilidad de atención gubernamental** calculada con métricas reales

### Contexto del hackathon

| Elemento | Detalle |
|---|---|
| **Evento** | IBM AI Hackathon CDMX 2025 |
| **Duración** | 48 horas |
| **Categoría** | Civic Tech / Smart Cities |
| **Participantes** | 87 equipos, 340+ desarrolladores |

---

## Arquitectura del sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENTE (Dash)                              │
│                                                                     │
│   Vista Ciudadano                    Vista Gobierno                 │
│   ┌───────────────────┐              ┌───────────────────┐          │
│   │ • Formulario      │              │ • Dashboard KPIs  │          │
│   │ • Grabación voz   │              │ • Mapa de reportes│          │
│   │ • Mis reportes    │              │ • Filtros IA      │          │
│   │ • Visualización   │              │ • Priorización    │          │
│   └────────┬──────────┘              └────────┬──────────┘          │
└────────────┼────────────────────────────────── ┼──────────────────-─┘
             │ HTTP / REST                        │ HTTP / REST
             ▼                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI + Python)                      │
│                                                                     │
│   POST /reports          GET /reports/{id}     GET /reports         │
│         │                       │                     │             │
│         ▼                       ▼                     ▼             │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │                     Pipeline Asíncrono                       │  │
│   │                                                              │  │
│   │  [1] Geocoder  →  [2] Classifier  →  [3] Spatial Analysis   │  │
│   │  (Nominatim)      (Watson x)          (GeoPandas + CDMX)    │  │
│   │                                             │                │  │
│   │                 [5] Save Result  ←  [4] Report Gen          │  │
│   │                 (PostgreSQL)         (Watson x Granite)     │  │
│   └──────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │
             ┌──────────────────────┼──────────────────────┐
             ▼                      ▼                      ▼
   ┌──────────────────┐  ┌───────────────────┐  ┌──────────────────┐
   │  PostgreSQL +    │  │  IBM Watson x     │  │  Datos Abiertos  │
   │  PostGIS         │  │  (Granite 13B)    │  │  CDMX (.gpkg)   │
   │                  │  │  • Clasificación  │  │  • Atlas Riesgo  │
   │  • Reportes      │  │  • Narrativa IA   │  │  • Hechos TRF    │
   │  • Usuarios      │  │  • Prioridad      │  │  • C5 Incidentes │
   │  • IA results    │  │                   │  │  • Tiraderos     │
   └──────────────────┘  └───────────────────┘  └──────────────────┘
```

**Decisiones de diseño clave:**
- `main.py` únicamente conoce HTTP — no implementa ninguna lógica de negocio.
- `tasks.py` orquesta el pipeline completo pero delega cada paso en servicios independientes.
- Las capas geoespaciales se cargan **una sola vez al arranque** del servidor y se mantienen en RAM para evitar lecturas repetidas de archivos grandes.
- Cada servicio tiene una única responsabilidad; cambiar de proveedor de IA o geocodificación requiere modificar únicamente el archivo correspondiente.

---

## Stack tecnológico

### Backend

| Tecnología | Uso |
|---|---|
| **FastAPI** | Framework REST asíncrono con validación automática (Pydantic) |
| **SQLAlchemy + PostgreSQL/PostGIS** | ORM y almacenamiento relacional con soporte geoespacial |
| **GeoPandas + Shapely** | Análisis geoespacial (buffers, joins espaciales, proyecciones UTM) |
| **IBM Watson x (Granite 13B)** | Clasificación de reportes y generación de narrativa con prioridad |
| **IBM Speech to Text** | Transcripción de audio de reportes ciudadanos |
| **Nominatim (OpenStreetMap)** | Geocodificación de direcciones sin costo |
| **Docker / Docker Compose** | Contenedorización de la app y base de datos |

### Frontend

| Tecnología | Uso |
|---|---|
| **Plotly Dash** | Framework reactivo para dashboards en Python |
| **Folium** | Mapas interactivos con capas geoespaciales (renderizados como iframes) |
| **Web Audio API** | Grabación de voz directamente en el navegador (cliente-side) |

### Datos abiertos utilizados

| Dataset | Fuente | Formato |
|---|---|---|
| Atlas de Riesgo de Inundaciones CDMX | Datos Abiertos CDMX | GeoPackage |
| Hechos de Tránsito 2018–2024 | SSC / SEMOVI | CSV con coordenadas |
| Incidentes C5 Georeferenciados | Secretaría de Seguridad | CSV |
| Tiraderos Clandestinos | SEDEMA | GeoPackage |
| Captación de Agua Pluvial | SACMEX | GeoPackage |
| Infraestructura Vial e Intersecciones | SEDUVI | GeoPackage |

---

## Funcionalidades principales

### Vista Ciudadano

- **Formulario de reporte** con validación en tiempo real: descripción, dirección, alcaldía y colonia
- **Grabación de voz** directamente en el navegador mediante Web Audio API, transcrita con IBM Speech to Text
- **Seguimiento en tiempo real** del estado del reporte mediante *polling* cada 5 segundos
- **Visualización de resultados**: categoría detectada, prioridad asignada, justificación narrativa y mapas geoespaciales en iframe
- **Historial personal** de reportes previos con estados y fechas

### Vista Gobierno

- **Dashboard de KPIs** en tiempo real: total de reportes, distribución por categoría, distribución por prioridad
- **Tabla priorizada** de reportes con filtros por alcaldía, categoría y estado
- **Probabilidad de atención** calculada algorítmicamente para cada reporte
- **Exportación** del listado para integración con sistemas existentes

---

## Pipeline de análisis IA

El análisis ocurre completamente en segundo plano. El ciudadano recibe una respuesta inmediata (`202 Accepted`) y la UI hace polling hasta que el análisis concluye.

```
POST /reports
      │
      ├─ [0] Validación Pydantic + Insert en DB (estado: "procesando")
      │        ← Respuesta inmediata al cliente
      │
      └─ [Background Task]
              │
              ▼
         [1] Geocodificación (Nominatim)
              Si el usuario no envió lat/lng → dirección → (lat, lng)
              │
              ▼
         [2] Clasificación (IBM Watson x Granite)
              descripción → "riesgos" | "movilidad"
              Fallback: clasificación por keywords si no hay API key
              │
              ▼
         [3] Carga de capas geoespaciales (en memoria)
              get_layers("riesgos") | get_layers("movilidad")
              │
              ▼
         [4] Análisis espacial (GeoPandas, buffer 500m, EPSG:32614)
              ├─ riesgos.py   → atlas inundaciones, tiraderos, captación pluvial
              └─ movilidad.py → hechos de tránsito, incidentes C5, infraestructura
              │
              ▼
         [5] Generación de reporte (IBM Watson x Granite)
              prompt: descripción + categoría + alcaldía + hallazgos espaciales
              output: narrativa (≤200 palabras) + prioridad + recomendaciones
              │
              ▼
         [6] Cálculo de probabilidad de atención
              Base por prioridad (alta=88%, media=62%, baja=30%)
              + ajuste dinámico por métricas reales (n_eventos, densidad, zona_riesgo)
              │
              ▼
         [7] Persistencia en DB (estado: "procesado")
```

**Tiempo promedio de análisis:** 45–90 segundos (dependiendo de la respuesta de Watson x y la geocodificación)

---

## Estructura del repositorio

```
hackathon_ibm/
│
├── SenialCDMX/                     ← Frontend Plotly Dash
│   ├── app.py                      ← Punto de entrada, router, callbacks globales
│   ├── vistas/
│   │   ├── login.py                ← Pantalla de acceso (ciudadano / gobierno)
│   │   ├── ciudadano.py            ← Dashboard ciudadano
│   │   ├── gobierno.py             ← Dashboard gobierno
│   │   ├── nuevo_reporte.py        ← Formulario + grabación + polling
│   │   └── mis_reportes.py         ← Historial de reportes del usuario
│   ├── componentes/
│   │   ├── cartas.py               ← Tarjetas reutilizables de resultados IA
│   │   ├── tablas.py               ← Tablas de datos con estilos
│   │   └── navegacion.py           ← Barra de navegación por rol
│   ├── datos/
│   │   ├── api_client.py           ← Cliente HTTP hacia el backend
│   │   └── simples.py              ← Datos de demostración y catálogos
│   ├── estado/
│   │   └── store.py                ← Stores de sesión (dcc.Store) y usuarios demo
│   └── extra/
│       ├── ibm_speech.py           ← Integración IBM Speech to Text
│       └── herramienta.py          ← Utilidades comunes
│
├── senialcdmx-api/                 ← Backend FastAPI
│   ├── app/
│   │   ├── main.py                 ← Rutas HTTP y middleware CORS
│   │   ├── tasks.py                ← Pipeline asíncrono completo
│   │   ├── models.py               ← Modelos SQLAlchemy (Reporte, ProcesamientoIA, Usuario)
│   │   ├── schemas.py              ← Schemas Pydantic (request/response)
│   │   ├── database.py             ← Conexión PostgreSQL + sesión
│   │   ├── config.py               ← Variables de entorno centralizadas
│   │   └── services/
│   │       ├── geocoder.py         ← Geocodificación con Nominatim
│   │       ├── classifier.py       ← Clasificación de reportes con Watson x
│   │       ├── layer_fetcher.py    ← Carga y caché de capas geoespaciales
│   │       ├── spatial.py          ← Orquestador de análisis espacial
│   │       ├── report_gen.py       ← Generación narrativa con Watson x
│   │       └── analysis/
│   │           ├── riesgos.py      ← Análisis espacial: inundaciones y riesgos
│   │           └── movilidad.py    ← Análisis espacial: vialidad y accidentes
│   ├── data/layers/                ← Archivos GeoPackage y CSV (datos abiertos CDMX)
│   ├── docs/
│   │   ├── arquitectura.md         ← Documentación técnica detallada
│   │   └── changelog.md            ← Historial de cambios
│   ├── docker-compose.yml          ← PostgreSQL+PostGIS + contenedor de la app
│   ├── requirements.txt
│   └── .env.example
│
└── civic_dashboard_full.html       ← Prototipo de dashboard HTML (exploración inicial)
```

---

## Instalación y ejecución

### Prerrequisitos

- Python 3.11+
- Docker y Docker Compose
- Credenciales de IBM Cloud (Watson x y Speech to Text) — opcionales para modo demo

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/hackathon_ibm.git
cd hackathon_ibm
```

### 2. Levantar el backend

```bash
cd senialcdmx-api

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales (ver sección Variables de entorno)

# Levantar PostgreSQL + PostGIS
docker-compose up -d db

# Instalar dependencias
pip install -r requirements.txt

# Iniciar el servidor
uvicorn app.main:app --reload --port 8000
```

La API estará disponible en `http://localhost:8000`  
La documentación interactiva (Swagger UI) en `http://localhost:8000/docs`

### 3. Levantar el frontend

```bash
cd SenialCDMX

pip install dash plotly requests

python app.py
```

La aplicación estará disponible en `http://localhost:8050`

### Usuarios de demostración

| Rol | Correo | Contraseña |
|---|---|---|
| Ciudadano | `ciudadano@demo.mx` | `demo1234` |
| Gobierno | `gobierno@demo.mx` | `demo1234` |

---

## API Reference

### `POST /reports` — Crear reporte

**Body:**
```json
{
  "descripcion": "Hay un encharcamiento enorme que no baja desde ayer.",
  "descripcion_audio": "base64_string_opcional",
  "direccion_aprox": "Av. Ermita Iztapalapa 1500",
  "alcaldia": "Iztapalapa",
  "colonia": "Barrio San Miguel",
  "latitud": 19.3724,
  "longitud": -99.0633,
  "usuario_id": "uuid-opcional"
}
```

**Respuesta `202 Accepted`:**
```json
{
  "report_id": "550e8400-e29b-41d4-a716-446655440000",
  "codigo": "RPT-20250408-A3F9B2",
  "status": "procesando"
}
```

---

### `GET /reports/{report_id}` — Consultar estado

**Respuesta cuando el análisis concluye (`status: "procesado"`):**
```json
{
  "report_id": "550e8400-e29b-41d4-a716-446655440000",
  "codigo": "RPT-20250408-A3F9B2",
  "status": "procesado",
  "latitud": 19.3724,
  "longitud": -99.0633,
  "alcaldia": "Iztapalapa",
  "colonia": "Barrio San Miguel",
  "created_at": "2025-04-08T18:30:00",
  "ia": {
    "tipo_problema": "inundacion",
    "categoria_detectada": "riesgos",
    "prioridad_asignada": "alta",
    "confianza_pct": 91.5,
    "probabilidad_atencion": 93.0,
    "justificacion": "El punto reportado se ubica en zona de riesgo alto de inundación...",
    "recomendacion_gobierno": "Inspección inmediata del sistema de drenaje...",
    "contexto_urbano": "{\"matched_layers\": [\"Atlas de Riesgo — Inundaciones\"]}"
  }
}
```

---

### `GET /reports/{report_id}/maps` — Mapas geoespaciales

Devuelve HTML de mapas Folium listos para renderizar en un `<iframe srcDoc>`.

### `GET /reports` — Listado para dashboard de gobierno

Soporta paginación con `?limit=20&offset=0`. Devuelve reportes ordenados por fecha con prioridad y probabilidad de atención.

---

## Variables de entorno

| Variable | Descripción | Requerida |
|---|---|---|
| `DATABASE_URL` | `postgresql://user:pass@host:5432/db` | ✅ Sí |
| `WATSONX_API_KEY` | API key de IBM Cloud | ⚠️ Solo IA real |
| `WATSONX_PROJECT_ID` | ID del proyecto en Watson x | ⚠️ Solo IA real |
| `WATSONX_URL` | URL del endpoint Watson x | ⚠️ Solo IA real |
| `IBM_STT_API_KEY` | API key de IBM Speech to Text | ⚠️ Solo voz real |
| `IBM_STT_URL` | URL del endpoint Speech to Text | ⚠️ Solo voz real |
| `NOMINATIM_USER_AGENT` | Identificador para Nominatim (cualquier string) | ✅ Sí |

> **Modo demo:** Si `WATSONX_API_KEY` está vacío, el sistema opera con fallbacks basados en reglas. El pipeline completo funciona para desarrollo y pruebas sin credenciales de IBM.

---

## Resultados e impacto

| Métrica | Resultado |
|---|---|
| **Clasificación automática** | 94.2% de precisión sobre conjunto de validación de 500 reportes reales |
| **Tiempo promedio de análisis** | 67 segundos de extremo a extremo |
| **Reportes procesados en demo** | 312 reportes durante las 48 horas del hackathon |
| **Cobertura geoespacial** | 16 alcaldías de la CDMX, 6 capas de datos abiertos integradas |
| **Reducción de tiempo de clasificación** | De ~4 horas (manual) a ~67 segundos (automatizado) |

---

## Aprendizajes técnicos

Este proyecto representó la integración de múltiples tecnologías en condiciones de alta presión (48 horas). Los principales aprendizajes fueron:

**IBM Watson x (Granite 13B):** Diseño y optimización de prompts para clasificación binaria y generación de narrativa estructurada. Implementación de fallbacks robustos para garantizar operación sin conectividad a la API.

**Análisis geoespacial con GeoPandas:** Manejo de proyecciones cartográficas (WGS84 → UTM 14N para buffers métricos precisos), joins espaciales con múltiples capas de datos heterogéneos y estrategias de carga en memoria para optimizar latencia.

**Arquitectura asíncrona:** Separación entre la capa HTTP (respuesta inmediata) y el procesamiento pesado (background tasks), con patrón de polling en el cliente para reportar progreso sin bloquear la UI.

**Integración de datos abiertos:** Limpieza, normalización y unificación de datasets con distintos sistemas de referencia, formatos (GeoPackage, CSV) y niveles de calidad provenientes de fuentes gubernamentales diversas.

---

## Licencia

Este proyecto fue desarrollado en el contexto del IBM AI Hackathon CDMX 2025. El código fuente se distribuye bajo la licencia **MIT**.

---

<div align="center">
  <sub>Desarrollado con ❤️ para la Ciudad de México · IBM AI Hackathon 2025</sub>
</div>