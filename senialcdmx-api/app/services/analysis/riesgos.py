"""
Análisis espacial — categoría "riesgos" (gestión de inundaciones).

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
from collections import Counter
from typing import Optional

import folium
import folium.plugins
import geopandas as gpd
from shapely.geometry import Point

logger = logging.getLogger(__name__)

BUFFER_RADIUS_M = 500
CRS_METRIC = "EPSG:32614"
CRS_GEO    = "EPSG:4326"

# Paleta de colores por nivel de riesgo
_COLOR_NIVEL = {
    "Muy Alto": "#7B0000",
    "Alto":     "#C0392B",
    "Medio":    "#E67E22",
    "Bajo":     "#F1C40F",
    "Muy Bajo": "#A8D8EA",
}
_COLOR_NIVEL_DEFAULT = "#AAAAAA"


# ── Helpers internos ──────────────────────────────────────────────────────────

def _make_buffer(lat: float, lng: float):
    pt = gpd.GeoDataFrame(geometry=[Point(lng, lat)], crs=CRS_GEO)
    buf = pt.to_crs(CRS_METRIC).buffer(BUFFER_RADIUS_M).to_crs(CRS_GEO)
    return buf.iloc[0]


def _filter_within(layer, buffer, name: str) -> gpd.GeoDataFrame:
    if layer is None or (hasattr(layer, "empty") and layer.empty):
        return gpd.GeoDataFrame()
    if "geometry" not in layer.columns or layer.geometry.isna().all():
        return gpd.GeoDataFrame()
    try:
        valid = layer[layer.geometry.notna()].copy()
        if valid.crs and valid.crs.to_epsg() != 4326:
            valid = valid.to_crs(CRS_GEO)
        result = valid[valid.geometry.intersects(buffer)]
        logger.debug("Capa %s: %d registros en buffer", name, len(result))
        return result
    except Exception as e:
        logger.error("Error filtrando %s: %s", name, e)
        return gpd.GeoDataFrame()


def _filtrar_capas(lat: float, lng: float, layers: dict) -> dict:
    """Filtra todas las capas de riesgos al buffer y las devuelve."""
    buffer = _make_buffer(lat, lng)
    return {
        "buffer":    buffer,
        "atlas":     _filter_within(layers.get("atlas_inundaciones"),    buffer, "atlas"),
        "niveles":   _filter_within(layers.get("niveles_inundacion"),    buffer, "niveles"),
        "tiraderos": _filter_within(layers.get("tiraderos_clandestinos"),buffer, "tiraderos"),
        "captacion": _filter_within(layers.get("captacion_pluvial"),     buffer, "captacion"),
        "av":        _filter_within(layers.get("areas_verdes"),          buffer, "areas_verdes"),
    }


def _detect_nivel_riesgo(atlas, niveles) -> tuple[bool, str]:
    for gdf, col_candidates in [
        (atlas,   ["intnsdd", "intns_nm", "nivel", "riesgo"]),
        (niveles, ["INUNDACION", "nivel", "riesgo"]),
    ]:
        if gdf is None or gdf.empty:
            continue
        col = next((c for c in col_candidates if c in gdf.columns), None)
        if col:
            val = str(gdf.iloc[0][col])
            if any(k in val for k in ["Muy Alto", "muy alto", "100", "alto", "Alto"]):
                return True, "alto"
            if any(k in val for k in ["Medio", "medio", "50"]):
                return True, "medio"
            if any(k in val for k in ["Bajo", "bajo"]):
                return True, "bajo"
            return True, "medio"
        if len(gdf) > 0:
            return True, "medio"
    return False, "ninguno"


def _area_verde_m2(av) -> float:
    if av is None or av.empty:
        return 0.0
    try:
        return float(av.to_crs(CRS_METRIC).geometry.area.sum())
    except Exception:
        return 0.0


# ── Función pública de análisis (sin cambios en firma) ────────────────────────

def analyze_riesgos(lat: float, lng: float, layers: dict) -> tuple[dict, dict]:
    """Retorna (metrics, layers_summary). Firma sin cambios para el pipeline."""
    fc = _filtrar_capas(lat, lng, layers)

    zona_riesgo, nivel_riesgo = _detect_nivel_riesgo(fc["atlas"], fc["niveles"])
    cobertura_av = _area_verde_m2(fc["av"])
    deficit_av   = cobertura_av < 70_000

    metrics = {
        "zona_riesgo_inundacion":   zona_riesgo,
        "nivel_riesgo":             nivel_riesgo,
        "n_presas_cercanas":        0,
        "n_puntos_captacion":       len(fc["captacion"]),
        "n_tiraderos":              len(fc["tiraderos"]),
        "cobertura_areas_verdes_m2": round(cobertura_av, 2),
        "deficit_areas_verdes":     deficit_av,
    }

    matched_layers, findings = [], []
    if zona_riesgo:
        matched_layers.append("Atlas de Riesgo — Inundaciones")
        findings.append(f"El punto está en zona de riesgo de inundación (nivel: {nivel_riesgo}).")
    if len(fc["tiraderos"]) > 0:
        matched_layers.append("Tiraderos Clandestinos")
        findings.append(f"{len(fc['tiraderos'])} tiradero(s) clandestino(s) en 500 m.")
    if len(fc["captacion"]) > 0:
        matched_layers.append("Sistema de Captación Pluvial")
        findings.append(f"{len(fc['captacion'])} punto(s) de captación pluvial cercanos.")
    if deficit_av:
        matched_layers.append("Inventario de Áreas Verdes")
        findings.append(f"Déficit de áreas verdes ({cobertura_av:,.0f} m² en 500 m).")
    elif len(fc["av"]) > 0:
        matched_layers.append("Inventario de Áreas Verdes")
        findings.append(f"Cobertura adecuada de áreas verdes ({cobertura_av:,.0f} m²).")
    if not findings:
        findings.append("No se encontraron factores de riesgo significativos en 500 m.")

    return metrics, {"matched_layers": matched_layers, "findings": findings}


# ── Generación de mapas ───────────────────────────────────────────────────────

def _base_map(lat: float, lng: float, buffer) -> folium.Map:
    """Mapa base con buffer y marcador del punto del reporte."""
    m = folium.Map(
        location=[lat, lng],
        zoom_start=15,
        tiles="CartoDB positron",
        control_scale=True,
    )
    # Buffer de análisis
    folium.Circle(
        location=[lat, lng],
        radius=BUFFER_RADIUS_M,
        color="#2D5A3D",
        weight=2,
        dash_array="8 4",
        fill=True,
        fill_color="#2D5A3D",
        fill_opacity=0.04,
        tooltip="Radio de análisis: 500 m",
    ).add_to(m)
    # Punto del reporte
    folium.Marker(
        location=[lat, lng],
        tooltip="📍 Punto del reporte",
        icon=folium.Icon(color="red", icon="exclamation-sign", prefix="glyphicon"),
    ).add_to(m)
    return m


def _add_poligonos(m: folium.Map, gdf: gpd.GeoDataFrame,
                   col_nivel: str, nombre_capa: str, opacidad: float = 0.5):
    """Agrega polígonos de riesgo coloreados por nivel."""
    if gdf is None or gdf.empty:
        return

    grupo = folium.FeatureGroup(name=nombre_capa, show=True)

    for _, row in gdf.iterrows():
        if row.geometry is None:
            continue
        nivel = str(row.get(col_nivel, "")) if col_nivel in gdf.columns else ""
        color = _COLOR_NIVEL.get(nivel, _COLOR_NIVEL_DEFAULT)
        tooltip_txt = f"<b>{nombre_capa}</b><br>Nivel: {nivel}" if nivel else nombre_capa

        try:
            geojson = folium.GeoJson(
                row.geometry.__geo_interface__,
                style_function=lambda _, c=color: {
                    "fillColor": c,
                    "color": c,
                    "weight": 1,
                    "fillOpacity": opacidad,
                },
                tooltip=tooltip_txt,
            )
            geojson.add_to(grupo)
        except Exception:
            pass

    grupo.add_to(m)


def mapas_riesgos(lat: float, lng: float, layers: dict) -> dict[str, folium.Map]:
    """
    Genera tres mapas folium para el análisis de riesgos:
      - 'atlas':          Polígonos del atlas de inundación + niveles de inundación
      - 'infraestructura': Tiraderos, captación pluvial y áreas verdes
      - 'general':        Vista conjunta de todas las capas
    """
    fc = _filtrar_capas(lat, lng, layers)
    buf = fc["buffer"]

    # ── Mapa 1: Atlas de Riesgo Hídrico ──────────────────────────────────────
    m_atlas = _base_map(lat, lng, buf)

    # Niveles de inundación (polígonos base, más transparentes)
    _add_poligonos(m_atlas, fc["niveles"], "INUNDACION",
                   "Niveles de inundación por colonia", opacidad=0.3)
    # Atlas de riesgo (polígonos más oscuros encima)
    _add_poligonos(m_atlas, fc["atlas"], "intnsdd",
                   "Atlas de riesgo — inundaciones", opacidad=0.6)

    # Leyenda
    _leyenda_niveles(m_atlas, "Intensidad de riesgo hídrico")
    folium.LayerControl().add_to(m_atlas)

    # ── Mapa 2: Infraestructura ───────────────────────────────────────────────
    m_infra = _base_map(lat, lng, buf)

    # Áreas verdes (polígonos verdes)
    _add_poligonos(m_infra, fc["av"], "", "Áreas verdes")
    if not fc["av"].empty:
        for _, row in fc["av"].iterrows():
            if row.geometry and row.geometry.geom_type in ("Polygon", "MultiPolygon"):
                c = row.geometry.centroid
                folium.Circle(
                    [c.y, c.x], radius=3,
                    color="#27AE60", fill=True, fill_color="#27AE60", fill_opacity=0.7,
                ).add_to(m_infra)

    # Puntos de captación pluvial
    grupo_cap = folium.FeatureGroup(name="Captación pluvial", show=True)
    for _, row in fc["captacion"].iterrows():
        if row.geometry is None:
            continue
        pt = row.geometry if row.geometry.geom_type == "Point" else row.geometry.centroid
        folium.CircleMarker(
            location=[pt.y, pt.x],
            radius=7, color="#1A5276", fill=True,
            fill_color="#2980B9", fill_opacity=0.85, weight=2,
            tooltip=f"💧 Captación pluvial",
        ).add_to(grupo_cap)
    grupo_cap.add_to(m_infra)

    # Tiraderos clandestinos
    grupo_tir = folium.FeatureGroup(name="Tiraderos clandestinos", show=True)
    for _, row in fc["tiraderos"].iterrows():
        if row.geometry is None:
            continue
        pt = row.geometry if row.geometry.geom_type == "Point" else row.geometry.centroid
        folium.CircleMarker(
            location=[pt.y, pt.x],
            radius=9, color="#7D3C98", fill=True,
            fill_color="#A569BD", fill_opacity=0.9, weight=2,
            tooltip="🗑️ Tiradero clandestino",
        ).add_to(grupo_tir)
    grupo_tir.add_to(m_infra)

    folium.LayerControl().add_to(m_infra)

    # ── Mapa 3: Vista general (todas las capas) ───────────────────────────────
    m_general = _base_map(lat, lng, buf)

    _add_poligonos(m_general, fc["niveles"], "INUNDACION",
                   "Niveles de inundación", opacidad=0.25)
    _add_poligonos(m_general, fc["atlas"], "intnsdd",
                   "Atlas de riesgo", opacidad=0.5)

    for _, row in fc["captacion"].iterrows():
        if row.geometry is None:
            continue
        pt = row.geometry if row.geometry.geom_type == "Point" else row.geometry.centroid
        folium.CircleMarker(
            [pt.y, pt.x], radius=6,
            color="#1A5276", fill=True, fill_color="#2980B9", fill_opacity=0.85,
            tooltip="💧 Captación pluvial",
        ).add_to(m_general)

    for _, row in fc["tiraderos"].iterrows():
        if row.geometry is None:
            continue
        pt = row.geometry if row.geometry.geom_type == "Point" else row.geometry.centroid
        folium.CircleMarker(
            [pt.y, pt.x], radius=8,
            color="#7D3C98", fill=True, fill_color="#A569BD", fill_opacity=0.9,
            tooltip="🗑️ Tiradero clandestino",
        ).add_to(m_general)

    _leyenda_niveles(m_general, "Intensidad de riesgo hídrico")
    folium.LayerControl().add_to(m_general)

    return {"atlas": m_atlas, "infraestructura": m_infra, "general": m_general}


def _leyenda_niveles(m: folium.Map, titulo: str):
    items_html = "".join(
        f'<li><span style="background:{c};display:inline-block;'
        f'width:14px;height:14px;margin-right:6px;border-radius:2px"></span>{n}</li>'
        for n, c in _COLOR_NIVEL.items()
    )
    legend_html = f"""
    <div style="position:fixed;bottom:30px;right:10px;z-index:9999;
                background:white;padding:12px 16px;border-radius:8px;
                box-shadow:2px 2px 6px rgba(0,0,0,.25);font-size:12px;
                font-family:sans-serif;min-width:160px">
        <b style="font-size:13px">{titulo}</b>
        <ul style="list-style:none;padding:0;margin:8px 0 0 0">{items_html}</ul>
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))
