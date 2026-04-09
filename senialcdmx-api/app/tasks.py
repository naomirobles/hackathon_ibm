"""
Pipeline asíncrono orquestado con FastAPI BackgroundTasks.

Flujo:
  1. Geocodificar si el usuario no envió coordenadas
  2. Watson x clasifica la descripción → "riesgos" | "movilidad"
  3. Cargar capas correspondientes desde data/layers/
  4. Ejecutar análisis espacial según categoría
  5. Watson x genera conclusión narrativa + prioridad
  6. Guardar resultado en procesamiento_ia y marcar reporte como "procesado"
"""
import json
import logging
import uuid

from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)

# Mapeo categoría interna Watson x → ENUM categoria_reporte de la DB
_CATEGORIA_DB = {
    "riesgos":   "medio_ambiente",
    "movilidad": "transporte",
    "otro":      "servicios",
}

# Prioridad → probabilidad de atención estimada
_PROB_ATENCION = {
    "alta":  88.0,
    "media": 62.0,
    "baja":  30.0,
}


def _coords_validas(valor) -> bool:
    """True si el valor es una coordenada real (no None y no el placeholder 0)."""
    if valor is None:
        return False
    try:
        return float(valor) != 0.0
    except (TypeError, ValueError):
        return False


async def run_pipeline(report_id: uuid.UUID, db: Session) -> None:
    reporte = db.query(models.Reporte).filter(models.Reporte.id == report_id).first()
    if not reporte:
        logger.error("Reporte %s no encontrado en DB", report_id)
        return

    try:
        from app.services.geocoder import geocode
        from app.services.classifier import classify
        from app.services.layer_fetcher import get_layers
        from app.services.spatial import spatial_analysis
        from app.services.report_gen import generate_report

        # 1. Geocodificar si no hay coordenadas reales (0.0 = placeholder)
        if not _coords_validas(reporte.latitud):
            lat, lng = await geocode(reporte)
            if lat is not None and lng is not None:
                reporte.latitud = lat
                reporte.longitud = lng
                db.commit()
                logger.info("Reporte %s geocodificado: %.6f, %.6f", report_id, lat, lng)
            else:
                logger.warning("No se pudo geocodificar el reporte %s", report_id)

        # 2. Clasificar descripción con Watson x
        category = await classify(reporte.descripcion)
        reporte.categoria = _CATEGORIA_DB.get(category, "infraestructura")
        db.commit()
        logger.info("Reporte %s clasificado como: %s", report_id, category)

        # 3. Cargar capas de la categoría
        layers = get_layers(category)

        # 4. Análisis espacial — usar coords reales si existen, sino None
        lat = float(reporte.latitud) if _coords_validas(reporte.latitud) else None
        lng = float(reporte.longitud) if _coords_validas(reporte.longitud) else None

        metrics, layers_summary = spatial_analysis(
            lat=lat,
            lng=lng,
            category=category,
            layers=layers,
            alcaldia=reporte.alcaldia or "",
        )

        # 5. Generar reporte narrativo con Watson x
        result = await generate_report(
            report=reporte,
            metrics=metrics,
            layers_summary=layers_summary,
            category=category,
        )

        # 6. Guardar en procesamiento_ia
        proc = db.query(models.ProcesamientoIA).filter(
            models.ProcesamientoIA.reporte_id == report_id
        ).first()

        if not proc:
            proc = models.ProcesamientoIA(reporte_id=report_id)
            db.add(proc)

        proc.tipo_problema          = _tipo_problema(category, reporte.descripcion)
        proc.categoria_detectada    = category
        proc.prioridad_asignada     = result.priority
        proc.confianza_pct          = 80.0
        proc.probabilidad_atencion  = _PROB_ATENCION.get(result.priority, 60.0)
        proc.justificacion          = result.conclusion
        proc.recomendacion_gobierno = "\n".join(result.actions) if result.actions else None
        proc.contexto_urbano        = json.dumps(layers_summary, ensure_ascii=False)

        reporte.estado = "procesado"
        db.commit()
        logger.info(
            "Reporte %s listo. Prioridad: %s | Prob. atención: %.0f%%",
            report_id, result.priority, proc.probabilidad_atencion,
        )

    except Exception as exc:
        logger.exception("Error en pipeline del reporte %s: %s", report_id, exc)
        try:
            reporte.estado = "cancelado"
            db.commit()
        except Exception:
            db.rollback()
        raise exc


def _tipo_problema(category: str, descripcion: str) -> str:
    """Deriva el tipo específico de problema a partir de categoría + texto."""
    text = descripcion.lower()
    if category == "riesgos":
        if any(k in text for k in ["inundación", "inundacion", "encharcamiento", "agua"]):
            return "inundacion"
        if any(k in text for k in ["tiradero", "basura", "residuos"]):
            return "tiradero_clandestino"
        if any(k in text for k in ["drenaje", "alcantarilla"]):
            return "drenaje"
        return "riesgo_natural"
    elif category == "movilidad":
        if any(k in text for k in ["bache", "hoyo", "hundimiento"]):
            return "bache"
        if any(k in text for k in ["accidente", "choque", "atropello"]):
            return "accidente_vial"
        if any(k in text for k in ["semáforo", "semaforo", "señal", "señalamiento"]):
            return "señalamiento_vial"
        if any(k in text for k in ["cruce", "peatonal", "paso"]):
            return "cruce_peatonal"
        return "infraestructura_vial"
    return "otro"
