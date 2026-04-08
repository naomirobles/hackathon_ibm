"""
Análisis espacial para la categoría "riesgos" (gestión de inundaciones).

Métricas producidas:
    zona_riesgo_inundacion   bool
    nivel_riesgo             "alto" | "medio" | "bajo" | "ninguno"
    n_presas_cercanas        int
    n_puntos_captacion       int
    n_tiraderos              int
    cobertura_areas_verdes_m2 float
    deficit_areas_verdes     bool
"""
import logging
from typing import Optional

import geopandas as gpd
from shapely.geometry import Point

logger = logging.getLogger(__name__)

# Radio de análisis en metros (UTM zona 14N)
BUFFER_RADIUS_M = 500

# CRS de trabajo para cálculos métricos
CRS_METRIC = "EPSG:32614"   # UTM zona 14N — Ciudad de México
CRS_GEO    = "EPSG:4326"    # WGS84


def _make_buffer(lat: float, lng: float) -> gpd.GeoDataFrame:
    """Devuelve un GeoDataFrame con el buffer de 500m alrededor del punto."""
    point = gpd.GeoDataFrame(geometry=[Point(lng, lat)], crs=CRS_GEO)
    point_utm = point.to_crs(CRS_METRIC)
    buffer_utm = point_utm.buffer(BUFFER_RADIUS_M)
    buffer_geo = buffer_utm.to_crs(CRS_GEO)
    return buffer_geo.iloc[0]


def _filter_within(
    layer: Optional[gpd.GeoDataFrame],
    buffer,
    name: str,
) -> Optional[gpd.GeoDataFrame]:
    """Filtra los registros de una capa que caen dentro del buffer."""
    if layer is None or layer.empty:
        logger.debug("Capa %s vacía o no disponible", name)
        return gpd.GeoDataFrame()

    if layer.geometry.isna().all() or not layer.geometry.notna().any():
        logger.debug("Capa %s sin geometría válida", name)
        return gpd.GeoDataFrame()

    try:
        valid = layer[layer.geometry.notna()].copy()
        if valid.crs and valid.crs.to_epsg() != 4326:
            valid = valid.to_crs(CRS_GEO)
        result = valid[valid.geometry.within(buffer)]
        logger.debug("Capa %s: %d registros en buffer", name, len(result))
        return result
    except Exception as e:
        logger.error("Error filtrando capa %s: %s", name, e)
        return gpd.GeoDataFrame()


def _detect_nivel_riesgo(atlas: gpd.GeoDataFrame, niveles: gpd.GeoDataFrame) -> tuple[bool, str]:
    """
    Determina si el punto está en zona de riesgo y el nivel.
    Busca columnas de nivel/riesgo en la capa de atlas e inundaciones.
    """
    if atlas is None or atlas.empty:
        return False, "ninguno"

    # Intentar detectar nivel desde atributos
    nivel_cols = [c for c in (atlas.columns if atlas is not None else [])
                  if any(kw in c.lower() for kw in ["nivel", "riesgo", "nivel_rie", "categoria"])]

    if nivel_cols and len(atlas) > 0:
        col = nivel_cols[0]
        val = str(atlas.iloc[0][col]).lower()
        if any(k in val for k in ["alto", "high", "3", "muy"]):
            return True, "alto"
        if any(k in val for k in ["medio", "med", "2"]):
            return True, "medio"
        if any(k in val for k in ["bajo", "low", "1"]):
            return True, "bajo"
        return True, "medio"  # en zona pero sin nivel claro → medio

    # Sin atributo de nivel: si hay registros en el buffer, hay riesgo
    if len(atlas) > 0:
        return True, "medio"

    if niveles is not None and len(niveles) > 0:
        return True, "medio"

    return False, "ninguno"


def _area_verde_m2(areas_verdes: Optional[gpd.GeoDataFrame]) -> float:
    """Suma el área verde (m²) dentro del buffer."""
    if areas_verdes is None or areas_verdes.empty:
        return 0.0
    try:
        av_utm = areas_verdes.to_crs(CRS_METRIC)
        return float(av_utm.geometry.area.sum())
    except Exception as e:
        logger.error("Error calculando área verde: %s", e)
        return 0.0


def analyze_riesgos(
    lat: float,
    lng: float,
    layers: dict,
) -> tuple[dict, dict]:
    """
    Ejecuta el análisis de riesgos para el punto dado.

    Returns:
        metrics (dict): métricas calculadas
        layers_summary (dict): matched_layers y findings para el reporte
    """
    buffer = _make_buffer(lat, lng)

    atlas     = _filter_within(layers.get("atlas_inundaciones"), buffer, "atlas_inundaciones")
    niveles   = _filter_within(layers.get("niveles_inundacion"), buffer, "niveles_inundacion")
    tiraderos = _filter_within(layers.get("tiraderos_clandestinos"), buffer, "tiraderos_clandestinos")
    captacion = _filter_within(layers.get("captacion_pluvial"), buffer, "captacion_pluvial")
    av        = _filter_within(layers.get("areas_verdes"), buffer, "areas_verdes")

    zona_riesgo, nivel_riesgo = _detect_nivel_riesgo(atlas, niveles)
    cobertura_av = _area_verde_m2(av)

    # Déficit de áreas verdes: OMS recomienda 9 m² por habitante
    # Aproximación simple: si la cobertura en el buffer es < 70 000 m² (~28% del buffer de 500m)
    deficit_av = cobertura_av < 70_000

    metrics = {
        "zona_riesgo_inundacion": zona_riesgo,
        "nivel_riesgo": nivel_riesgo,
        "n_presas_cercanas": 0,  # no hay capa de presas en los datos actuales
        "n_puntos_captacion": len(captacion),
        "n_tiraderos": len(tiraderos),
        "cobertura_areas_verdes_m2": round(cobertura_av, 2),
        "deficit_areas_verdes": deficit_av,
    }

    # Construir layers_summary legible para humanos / Watson x
    matched_layers: list[str] = []
    findings: list[str] = []

    if zona_riesgo:
        matched_layers.append("Atlas de Riesgo — Inundaciones")
        findings.append(
            f"El punto se encuentra en zona de riesgo de inundación (nivel: {nivel_riesgo})."
        )

    if len(tiraderos) > 0:
        matched_layers.append("Tiraderos Clandestinos")
        findings.append(
            f"Se detectaron {len(tiraderos)} tiradero(s) clandestino(s) en un radio de 500 m."
        )

    if len(captacion) > 0:
        matched_layers.append("Sistema de Captación Pluvial")
        findings.append(
            f"Existen {len(captacion)} punto(s) de captación pluvial cercanos."
        )

    if deficit_av:
        matched_layers.append("Inventario de Áreas Verdes")
        findings.append(
            f"Déficit de áreas verdes detectado (cobertura: {cobertura_av:,.0f} m² en 500 m)."
        )
    elif len(av) > 0:
        matched_layers.append("Inventario de Áreas Verdes")
        findings.append(
            f"Cobertura de áreas verdes adecuada ({cobertura_av:,.0f} m² en 500 m)."
        )

    if not findings:
        findings.append("No se encontraron factores de riesgo significativos en el radio de 500 m.")

    layers_summary = {
        "matched_layers": matched_layers,
        "findings": findings,
    }

    logger.info("Análisis riesgos completo: %s", metrics)
    return metrics, layers_summary
