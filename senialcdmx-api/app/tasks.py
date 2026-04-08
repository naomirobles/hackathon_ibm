"""
Pipeline asíncrono orquestado con FastAPI BackgroundTasks.

Flujo:
  1. Geocodificar si el usuario no envió coordenadas
  2. Watson x clasifica la descripción → "riesgos" | "movilidad"
  3. Cargar capas correspondientes desde data/layers/
  4. Ejecutar análisis espacial según categoría
  5. Watson x genera conclusión narrativa + prioridad
  6. Guardar resultado y marcar el reporte como "ready"
"""
import logging

from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)


async def run_pipeline(report_id: int, db: Session) -> None:
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        logger.error("Reporte %d no encontrado en DB", report_id)
        return

    try:
        from app.services.geocoder import geocode
        from app.services.classifier import classify
        from app.services.layer_fetcher import get_layers
        from app.services.spatial import spatial_analysis
        from app.services.report_gen import generate_report

        # 1. Geocodificar si el usuario no puso marcador en el mapa
        if not report.lat:
            lat, lng = await geocode(report)
            if lat and lng:
                report.lat = lat
                report.lng = lng
                db.commit()
                logger.info("Reporte %d geocodificado: %.6f, %.6f", report_id, lat, lng)
            else:
                logger.warning("No se pudo geocodificar el reporte %d", report_id)

        # 2. Watson x clasifica la descripción del reporte
        category = await classify(report.description)
        logger.info("Reporte %d clasificado como: %s", report_id, category)

        # 3. Cargar capas correspondientes a la categoría desde data/layers/
        layers = get_layers(category)

        # 4. Ejecutar análisis espacial según categoría
        metrics, layers_summary = spatial_analysis(
            lat=report.lat,
            lng=report.lng,
            category=category,
            layers=layers,
            alcaldia=report.alcaldia or "",
        )

        # 5. Watson x recibe las métricas + hallazgos y genera:
        #    - conclusión narrativa
        #    - prioridad: "alta" | "media" | "baja"
        #    - propuestas de acción
        #
        #    TODO post-hackathon: pasar interpretación automática de métricas como input.
        result = await generate_report(
            report=report,
            metrics=metrics,
            layers_summary=layers_summary,
            category=category,
            interpretation=None,
        )

        # 6. Guardar resultado completo y marcar reporte como listo
        report.category = category
        report.priority = result.priority
        report.analysis = result.conclusion
        report.layers_summary = layers_summary
        report.status = "ready"
        db.commit()
        logger.info("Reporte %d procesado correctamente. Prioridad: %s", report_id, result.priority)

    except Exception as exc:
        logger.exception("Error en pipeline del reporte %d: %s", report_id, exc)
        report.status = "error"
        db.commit()
        raise exc
