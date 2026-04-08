import uuid
from datetime import datetime

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

app = FastAPI(title="SeñalCDMX API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Precarga todas las capas GeoJSON/GeoPackage al arrancar el servidor."""
    from app.services.layer_fetcher import load_all_layers
    load_all_layers()


@app.post("/reports", response_model=schemas.ReportCreatedResponse, status_code=202)
async def create_report(
    payload: schemas.ReportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    reporte = models.Reporte(
        descripcion=payload.descripcion,
        descripcion_audio=payload.descripcion_audio,
        direccion_aprox=payload.direccion_aprox,
        alcaldia=payload.alcaldia,
        colonia=payload.colonia,
        ciudad=payload.ciudad,
        latitud=payload.latitud,
        longitud=payload.longitud,
        fuente_input=payload.fuente_input,
        tiene_imagen=payload.tiene_imagen,
        usuario_id=uuid.UUID(payload.usuario_id) if payload.usuario_id else None,
        estado="processing",
    )
    db.add(reporte)
    db.commit()
    db.refresh(reporte)

    # Generar código legible después de obtener el ID
    reporte.codigo = f"RPT-{datetime.utcnow().year}-{reporte.id:05d}"
    db.commit()

    from app.tasks import run_pipeline
    background_tasks.add_task(run_pipeline, reporte.id, db)

    return schemas.ReportCreatedResponse(
        report_id=reporte.id,
        codigo=reporte.codigo,
        status="processing",
    )


@app.get("/reports/{report_id}", response_model=schemas.ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    reporte = db.query(models.Reporte).filter(models.Reporte.id == report_id).first()
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
        report_id=reporte.id,
        codigo=reporte.codigo,
        status=reporte.estado,
        latitud=float(reporte.latitud) if reporte.latitud is not None else None,
        longitud=float(reporte.longitud) if reporte.longitud is not None else None,
        alcaldia=reporte.alcaldia,
        colonia=reporte.colonia,
        created_at=reporte.created_at,
        ia=ia_data,
    )


@app.get("/reports", response_model=list[schemas.ReportListItem])
def list_reports(
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Lista reportes con su prioridad — útil para el dashboard."""
    reportes = (
        db.query(models.Reporte)
        .order_by(models.Reporte.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for r in reportes:
        prioridad = r.procesamiento.prioridad_asignada if r.procesamiento else None
        prob = float(r.procesamiento.probabilidad_atencion) if r.procesamiento and r.procesamiento.probabilidad_atencion else None
        items.append(schemas.ReportListItem(
            report_id=r.id,
            codigo=r.codigo,
            status=r.estado,
            categoria=r.categoria,
            alcaldia=r.alcaldia,
            prioridad=prioridad,
            probabilidad_atencion=prob,
            created_at=r.created_at,
        ))
    return items
