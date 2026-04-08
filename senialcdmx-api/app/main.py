from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

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
    report = models.Report(**payload.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)

    from app.tasks import run_pipeline
    background_tasks.add_task(run_pipeline, report.id, db)

    return schemas.ReportCreatedResponse(report_id=report.id, status="processing")


@app.get("/reports/{report_id}", response_model=schemas.ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    layers_summary = None
    if report.layers_summary:
        layers_summary = schemas.LayersSummary(**report.layers_summary)

    return schemas.ReportResponse(
        report_id=report.id,
        status=report.status,
        category=report.category,
        priority=report.priority,
        lat=report.lat,
        lng=report.lng,
        analysis=report.analysis,
        layers_summary=layers_summary,
        created_at=report.created_at,
    )
