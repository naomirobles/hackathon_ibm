import uuid
from datetime import datetime

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import SessionLocal, get_db

app = FastAPI(title="SeñalCDMX API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# UUID fijo para reportes sin usuario autenticado
UUID_ANONIMO = uuid.UUID("00000000-0000-4000-8000-000000000001")


@app.on_event("startup")
async def startup_event():
    # 1. Crear usuario anónimo si no existe (para reportes sin auth)
    db = SessionLocal()
    try:
        existe = db.query(models.Usuario).filter(models.Usuario.id == UUID_ANONIMO).first()
        if not existe:
            anonimo = models.Usuario(
                id=UUID_ANONIMO,
                nombre_completo="Ciudadano Anónimo",
                correo="anonimo@senialcdmx.mx",
                contrasena_hash="",
                rol="ciudadano",
            )
            db.add(anonimo)
            db.commit()
    finally:
        db.close()

    # 2. Precargar capas geoespaciales en memoria
    from app.services.layer_fetcher import load_all_layers
    load_all_layers()


@app.post("/reports", response_model=schemas.ReportCreatedResponse, status_code=202)
async def create_report(
    payload: schemas.ReportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Resolver usuario — si viene UUID válido en el payload, usarlo; si no, anónimo
    if payload.usuario_id:
        try:
            uid = uuid.UUID(payload.usuario_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="usuario_id no es un UUID válido")
    else:
        uid = UUID_ANONIMO

    # Generar codigo antes del insert (el campo es NOT NULL en la DB)
    codigo = f"RPT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    reporte = models.Reporte(
        codigo=codigo,
        usuario_id=uid,
        descripcion=payload.descripcion,
        descripcion_audio=payload.descripcion_audio,
        direccion_aprox=payload.direccion_aprox,
        alcaldia=payload.alcaldia,
        colonia=payload.colonia,
        # lat/lng NOT NULL en DB — usar 0 si no se envían (se actualizan en pipeline)
        latitud=payload.latitud if payload.latitud is not None else 0,
        longitud=payload.longitud if payload.longitud is not None else 0,
        # categoria NOT NULL — placeholder hasta que Watson x clasifique
        categoria="infraestructura",
        estado="procesando",
    )
    db.add(reporte)
    db.commit()
    db.refresh(reporte)

    from app.tasks import run_pipeline
    background_tasks.add_task(run_pipeline, reporte.id, db)

    return schemas.ReportCreatedResponse(
        report_id=str(reporte.id),
        codigo=reporte.codigo,
        status=str(reporte.estado),
    )


@app.get("/reports/{report_id}", response_model=schemas.ReportResponse)
def get_report(report_id: str, db: Session = Depends(get_db)):
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="report_id no es un UUID válido")

    reporte = db.query(models.Reporte).filter(models.Reporte.id == rid).first()
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    ia_data = None
    if reporte.procesamiento:
        p = reporte.procesamiento
        ia_data = schemas.ProcesamientoIAResponse(
            tipo_problema=p.tipo_problema,
            categoria_detectada=p.categoria_detectada,
            prioridad_asignada=p.prioridad_asignada,
            confianza_pct=float(p.confianza_pct) if p.confianza_pct is not None else None,
            probabilidad_atencion=float(p.probabilidad_atencion) if p.probabilidad_atencion is not None else None,
            justificacion=p.justificacion,
            recomendacion_gobierno=p.recomendacion_gobierno,
            contexto_urbano=p.contexto_urbano,
        )

    return schemas.ReportResponse(
        report_id=str(reporte.id),
        codigo=reporte.codigo,
        status=str(reporte.estado),
        latitud=float(reporte.latitud) if reporte.latitud is not None else None,
        longitud=float(reporte.longitud) if reporte.longitud is not None else None,
        alcaldia=reporte.alcaldia,
        colonia=reporte.colonia,
        created_at=reporte.created_at,
        ia=ia_data,
    )


# Mapeo DB category → categoría de análisis espacial
_DB_TO_ANALYSIS = {
    "medio_ambiente":  "riesgos",
    "areas_verdes":    "riesgos",
    "servicios":       "movilidad",
    "infraestructura": "movilidad",
    "transporte":      "movilidad",
    "seguridad":       "movilidad",
}


@app.get("/reports/{report_id}/maps")
def get_report_maps(report_id: str, db: Session = Depends(get_db)):
    """
    Genera los mapas folium del análisis espacial para un reporte.
    Devuelve HTML strings listos para renderizar en un <iframe srcDoc>.
    La categoría se mapea siempre a 'riesgos' o 'movilidad'.
    """
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="report_id no es un UUID válido")

    reporte = db.query(models.Reporte).filter(models.Reporte.id == rid).first()
    if not reporte:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    lat = float(reporte.latitud)  if reporte.latitud  and float(reporte.latitud)  != 0 else None
    lng = float(reporte.longitud) if reporte.longitud and float(reporte.longitud) != 0 else None
    if lat is None or lng is None:
        raise HTTPException(status_code=422, detail="Reporte sin coordenadas válidas")

    # Determinar categoría de análisis
    proc = reporte.procesamiento
    analysis_cat = (proc.categoria_detectada if proc and proc.categoria_detectada in ("riesgos", "movilidad") else None)
    if not analysis_cat:
        cat_db = str(reporte.categoria) if reporte.categoria else "infraestructura"
        analysis_cat = _DB_TO_ANALYSIS.get(cat_db, "movilidad")

    from app.services.layer_fetcher import get_layers
    layers = get_layers(analysis_cat)

    try:
        if analysis_cat == "riesgos":
            from app.services.analysis.riesgos import mapas_riesgos
            mapas = mapas_riesgos(lat, lng, layers)
        else:
            from app.services.analysis.movilidad import mapas_movilidad
            mapas = mapas_movilidad(lat, lng, layers, reporte.alcaldia or "")

        return {
            "category": analysis_cat,
            "maps": {k: m._repr_html_() for k, m in mapas.items()},
        }
    except Exception as exc:
        logger.error("Error generando mapas para reporte %s: %s", report_id, exc)
        raise HTTPException(status_code=500, detail=f"Error generando mapas: {exc}")


@app.get("/reports", response_model=list[schemas.ReportListItem])
def list_reports(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Lista reportes con prioridad — para el dashboard de gobierno."""
    reportes = (
        db.query(models.Reporte)
        .order_by(models.Reporte.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        schemas.ReportListItem(
            report_id=str(r.id),
            codigo=r.codigo,
            status=str(r.estado),
            categoria=r.categoria,
            alcaldia=r.alcaldia,
            prioridad=r.procesamiento.prioridad_asignada if r.procesamiento else None,
            probabilidad_atencion=float(r.procesamiento.probabilidad_atencion)
                if r.procesamiento and r.procesamiento.probabilidad_atencion else None,
            created_at=r.created_at,
        )
        for r in reportes
    ]
