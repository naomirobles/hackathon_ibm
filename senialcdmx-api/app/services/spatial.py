"""
Orquestador del análisis espacial.
Delega a riesgos.py o movilidad.py según la categoría del reporte.
"""
import logging
from typing import Optional

from app.services.analysis.movilidad import analyze_movilidad
from app.services.analysis.riesgos import analyze_riesgos

logger = logging.getLogger(__name__)


def spatial_analysis(
    lat: float,
    lng: float,
    category: str,
    layers: dict,
    alcaldia: str = "",
) -> tuple[dict, dict]:
    """
    Ejecuta el análisis espacial correspondiente a la categoría.

    Args:
        lat, lng: coordenadas del reporte
        category: "riesgos" | "movilidad"
        layers: dict de GeoDataFrames cargados por layer_fetcher
        alcaldia: nombre de la alcaldía (usado como fallback en movilidad)

    Returns:
        (metrics, layers_summary)
        metrics: dict con métricas numéricas/booleanas
        layers_summary: dict con 'matched_layers' y 'findings'
    """
    if lat is None or lng is None:
        logger.error("Coordenadas no disponibles para análisis espacial")
        return {}, {"matched_layers": [], "findings": ["Coordenadas no disponibles."]}

    if category == "riesgos":
        return analyze_riesgos(lat, lng, layers)
    elif category == "movilidad":
        return analyze_movilidad(lat, lng, layers, alcaldia=alcaldia)
    else:
        logger.warning("Categoría '%s' no reconocida — forzando análisis de movilidad", category)
        return analyze_movilidad(lat, lng, layers, alcaldia=alcaldia)
