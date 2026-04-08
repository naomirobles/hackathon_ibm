from sqlalchemy.orm import Session

from app import models


async def run_pipeline(report_id: int, db: Session):
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        return

    try:
        from app.services.geocoder import geocode
        from app.services.classifier import classify
        from app.services.layer_fetcher import fetch_layers
        from app.services.spatial import spatial_analysis
        from app.services.report_gen import generate_report

        # 1. Geocodificar si el usuario no puso coordenadas
        if not report.lat:
            report.lat, report.lng = await geocode(report)
            db.commit()

        # 2. Clasificar con Watson x
        category = await classify(report.description)

        # 3. Cargar capas relevantes
        layers_gdf = fetch_layers(category)

        # 4. Análisis espacial (buffer 500m)
        findings = spatial_analysis(report.lat, report.lng, layers_gdf)

        # 5. Generar reporte con Watson x
        analysis_text, priority = await generate_report(report, findings)

        # 6. Guardar y marcar como listo
        report.category = category
        report.analysis = analysis_text
        report.priority = priority
        report.layers_summary = findings
        report.status = "ready"
        db.commit()

    except Exception as exc:
        report.status = "error"
        db.commit()
        raise exc
