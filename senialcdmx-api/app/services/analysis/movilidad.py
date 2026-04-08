"""
Análisis espacial para la categoría "movilidad" (seguridad en cruces peatonales).

Métricas producidas:
    n_hechos_transito        int   — hechos de tránsito en radio 500m
    n_incidentes_c5          int   — incidentes reportados por ciudadanos (C5)
    n_infracciones_alcaldia  int   — infracciones filtradas por alcaldía (sin coords)
    intersecciones_riesgo    list  — nombres de intersecciones con más de 1 incidente
    densidad_incidentes      float — (hechos + incidentes) / km²
    tipo_incidente_frecuente str   — tipo de incidente más frecuente en el buffer
"""
import logging
import math
from collections import Counter
from typing import Optional

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

logger = logging.getLogger(__name__)

BUFFER_RADIUS_M = 500
CRS_METRIC = "EPSG:32614"
CRS_GEO    = "EPSG:4326"

# Área del buffer en km² (π * r²)
BUFFER_AREA_KM2 = math.pi * (BUFFER_RADIUS_M / 1000) ** 2


def _make_buffer(lat: float, lng: float):
    point = gpd.GeoDataFrame(geometry=[Point(lng, lat)], crs=CRS_GEO)
    point_utm = point.to_crs(CRS_METRIC)
    buffer_utm = point_utm.buffer(BUFFER_RADIUS_M)
    return buffer_utm.to_crs(CRS_GEO).iloc[0]


def _filter_within(
    layer: Optional[gpd.GeoDataFrame],
    buffer,
    name: str,
) -> gpd.GeoDataFrame:
    if layer is None or layer.empty:
        return gpd.GeoDataFrame()
    if "geometry" not in layer.columns or layer.geometry.isna().all():
        return gpd.GeoDataFrame()
    # Ignorar registros sin geometría
    valid = layer[layer.geometry.notna()].copy()
    if valid.empty:
        return gpd.GeoDataFrame()
    try:
        if valid.crs and valid.crs.to_epsg() != 4326:
            valid = valid.to_crs(CRS_GEO)
        result = valid[valid.geometry.within(buffer)]
        logger.debug("Capa %s: %d registros en buffer", name, len(result))
        return result
    except Exception as e:
        logger.error("Error filtrando capa %s: %s", name, e)
        return gpd.GeoDataFrame()


def _filter_by_alcaldia(
    layer,   # GeoDataFrame o DataFrame plano
    alcaldia: str,
) -> pd.DataFrame:
    """Filtrado por atributo para capas sin coordenadas (ej: infracciones)."""
    if layer is None or (hasattr(layer, "empty") and layer.empty):
        return pd.DataFrame()
    alcaldia_col = next(
        (c for c in layer.columns if "alcaldia" in c.lower()), None
    )
    if not alcaldia_col or not alcaldia:
        return pd.DataFrame()
    mask = layer[alcaldia_col].astype(str).str.upper().str.contains(
        alcaldia.upper(), na=False
    )
    return layer[mask]


def _intersecciones_riesgo(hechos: gpd.GeoDataFrame, incidentes: gpd.GeoDataFrame) -> list[str]:
    """
    Identifica intersecciones con alta concentración de eventos.
    Usa columnas 'punto_1'/'punto_2' (hechos) o 'tipo_incidente_c4' (incidentes).
    """
    puntos: list[str] = []

    if not hechos.empty:
        for col in ["punto_1", "punto_2", "interseccion"]:
            if col in hechos.columns:
                puntos.extend(hechos[col].dropna().astype(str).tolist())

    counter = Counter(puntos)
    return [loc for loc, cnt in counter.most_common(5) if cnt >= 2]


def _tipo_frecuente(hechos: gpd.GeoDataFrame, incidentes: gpd.GeoDataFrame) -> str:
    tipos: list[str] = []
    for df, col in [
        (hechos, "tipo_evento"),
        (incidentes, "tipo_incidente_c4"),
        (incidentes, "incidente_c4"),
    ]:
        if not df.empty and col in df.columns:
            tipos.extend(df[col].dropna().astype(str).tolist())
    if not tipos:
        return "sin datos"
    return Counter(tipos).most_common(1)[0][0]


def analyze_movilidad(
    lat: float,
    lng: float,
    layers: dict,
    alcaldia: str = "",
) -> tuple[dict, dict]:
    """
    Ejecuta el análisis de movilidad/seguridad vial para el punto dado.

    Returns:
        metrics (dict): métricas calculadas
        layers_summary (dict): matched_layers y findings para el reporte
    """
    buffer = _make_buffer(lat, lng)

    hechos    = _filter_within(layers.get("hechos_transito"), buffer, "hechos_transito")
    incidentes = _filter_within(layers.get("incidentes_c5"), buffer, "incidentes_c5")
    # infracciones sin coords — filtrar por alcaldía
    infracciones_df = _filter_by_alcaldia(layers.get("infracciones"), alcaldia)

    intersecciones = _intersecciones_riesgo(hechos, incidentes)
    tipo_frec = _tipo_frecuente(hechos, incidentes)
    densidad = (len(hechos) + len(incidentes)) / BUFFER_AREA_KM2

    metrics = {
        "n_hechos_transito": len(hechos),
        "n_incidentes_c5": len(incidentes),
        "n_infracciones_alcaldia": len(infracciones_df),
        "intersecciones_riesgo": intersecciones,
        "densidad_incidentes": round(densidad, 2),
        "tipo_incidente_frecuente": tipo_frec,
    }

    # Construir layers_summary
    matched_layers: list[str] = []
    findings: list[str] = []

    if len(hechos) > 0:
        matched_layers.append("Hechos de Tránsito 2023")
        findings.append(
            f"Se registraron {len(hechos)} hecho(s) de tránsito en un radio de 500 m."
        )

    if len(incidentes) > 0:
        matched_layers.append("Incidentes Viales C5")
        findings.append(
            f"Se reportaron {len(incidentes)} incidente(s) viales al C5 en el área."
        )

    if intersecciones:
        matched_layers.append("Intersecciones de Alto Riesgo")
        findings.append(
            f"Intersecciones con mayor concentración de eventos: {', '.join(intersecciones[:3])}."
        )

    if tipo_frec != "sin datos":
        findings.append(f"Tipo de incidente más frecuente en el área: {tipo_frec}.")

    findings.append(
        f"Densidad de incidentes en el buffer: {densidad:.1f} eventos/km²."
    )

    if len(infracciones_df) > 0:
        matched_layers.append("Infracciones al Reglamento de Tránsito")
        findings.append(
            f"{len(infracciones_df)} infracción(es) registradas en la alcaldía {alcaldia}."
        )

    if not matched_layers:
        findings.append("No se encontraron incidentes viales registrados en el radio de 500 m.")

    layers_summary = {
        "matched_layers": matched_layers,
        "findings": findings,
    }

    logger.info("Análisis movilidad completo: %s", metrics)
    return metrics, layers_summary
