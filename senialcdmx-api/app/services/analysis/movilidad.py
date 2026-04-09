"""
Análisis espacial — categoría "movilidad" (seguridad en cruces peatonales).

Métricas producidas:
    n_hechos_transito        int
    n_incidentes_c5          int
    n_infracciones_alcaldia  int
    intersecciones_riesgo    list[str]
    densidad_incidentes      float
    tipo_incidente_frecuente str
"""
import logging
import math
from collections import Counter, defaultdict
from typing import Optional

import folium
import folium.plugins
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

logger = logging.getLogger(__name__)

BUFFER_RADIUS_M  = 500
CRS_METRIC       = "EPSG:32614"
CRS_GEO          = "EPSG:4326"
BUFFER_AREA_KM2  = math.pi * (BUFFER_RADIUS_M / 1000) ** 2

# Radio para contar incidentes cerca de una intersección (metros)
_RADIO_INTER_M = 80


# ── Helpers internos ──────────────────────────────────────────────────────────

def _make_buffer(lat: float, lng: float):
    pt = gpd.GeoDataFrame(geometry=[Point(lng, lat)], crs=CRS_GEO)
    return pt.to_crs(CRS_METRIC).buffer(BUFFER_RADIUS_M).to_crs(CRS_GEO).iloc[0]


def _filter_within(layer, buffer, name: str) -> gpd.GeoDataFrame:
    if layer is None or (hasattr(layer, "empty") and layer.empty):
        return gpd.GeoDataFrame()
    if "geometry" not in layer.columns or layer.geometry.isna().all():
        return gpd.GeoDataFrame()
    try:
        valid = layer[layer.geometry.notna()].copy()
        if valid.crs and valid.crs.to_epsg() != 4326:
            valid = valid.to_crs(CRS_GEO)
        result = valid[valid.geometry.within(buffer)]
        logger.debug("Capa %s: %d registros", name, len(result))
        return result
    except Exception as e:
        logger.error("Error filtrando %s: %s", name, e)
        return gpd.GeoDataFrame()


def _filter_by_alcaldia(layer, alcaldia: str) -> pd.DataFrame:
    if layer is None or (hasattr(layer, "empty") and layer.empty):
        return pd.DataFrame()
    col = next((c for c in layer.columns if "alcaldia" in c.lower()), None)
    if not col or not alcaldia:
        return pd.DataFrame()
    return layer[layer[col].astype(str).str.upper().str.contains(alcaldia.upper(), na=False)]


def _filtrar_capas(lat: float, lng: float, layers: dict, alcaldia: str = "") -> dict:
    buffer = _make_buffer(lat, lng)
    calles_raw = layers.get("calles")
    calles_buf = gpd.GeoDataFrame()
    if calles_raw is not None and not calles_raw.empty and "geometry" in calles_raw.columns:
        try:
            valid = calles_raw[calles_raw.geometry.notna()].copy()
            if valid.crs and valid.crs.to_epsg() != 4326:
                valid = valid.to_crs(CRS_GEO)
            calles_buf = valid[valid.geometry.intersects(buffer)]
        except Exception as e:
            logger.error("Error filtrando CALLES: %s", e)
    return {
        "buffer":       buffer,
        "hechos":       _filter_within(layers.get("hechos_transito"), buffer, "hechos"),
        "incidentes":   _filter_within(layers.get("incidentes_c5"),   buffer, "incidentes"),
        "infracciones": _filter_by_alcaldia(layers.get("infracciones"), alcaldia),
        "calles":       calles_buf,
    }


def _tipo_frecuente(hechos, incidentes) -> str:
    tipos = []
    for df, col in [(hechos, "tipo_evento"), (incidentes, "tipo_incidente_c4"),
                    (incidentes, "incidente_c4")]:
        if not df.empty and col in df.columns:
            tipos.extend(df[col].dropna().astype(str).tolist())
    return Counter(tipos).most_common(1)[0][0] if tipos else "sin datos"


def _intersecciones_por_nombres(hechos, incidentes) -> list[str]:
    """Intersecciones frecuentes desde atributos de texto de hechos de tránsito."""
    puntos = []
    if not hechos.empty:
        for col in ["punto_1", "punto_2", "interseccion"]:
            if col in hechos.columns:
                puntos.extend(hechos[col].dropna().astype(str).tolist())
    return [loc for loc, cnt in Counter(puntos).most_common(5) if cnt >= 2]


# ── Detección geométrica de intersecciones de la red vial ────────────────────

def detectar_intersecciones_red_vial(
    calles: gpd.GeoDataFrame,
    hechos: gpd.GeoDataFrame,
    incidentes: gpd.GeoDataFrame,
    grid_m: int = 15,
) -> list[dict]:
    """
    Detecta intersecciones reales de la red vial dentro del buffer.

    Algoritmo:
    1. Extraer todos los endpoints de segmentos de calle (en UTM, metros).
    2. Agrupar endpoints en una grilla de `grid_m` × `grid_m` metros.
       Un grupo con ≥ 3 endpoints representa una intersección real.
    3. Para cada intersección, contar incidentes en radio de 80m.
    4. Obtener nombres de calles concurrentes (nom_vialid).

    Returns:
        Lista de dicts con: lat, lng, n_incidentes, calles (str), nivel_riesgo
    """
    if calles is None or calles.empty:
        return []

    try:
        calles_utm = calles.to_crs(CRS_METRIC)
    except Exception:
        return []

    # 1. Extraer endpoints con nombre de vialidad
    grid: defaultdict[tuple, list] = defaultdict(list)

    for _, row in calles_utm.iterrows():
        geom = row.geometry
        nombre = str(row.get("nom_vialid", "")).strip()
        coords = []
        if geom is None:
            continue
        if geom.geom_type == "LineString":
            coords = [geom.coords[0], geom.coords[-1]]
        elif geom.geom_type == "MultiLineString":
            for seg in geom.geoms:
                coords += [seg.coords[0], seg.coords[-1]]
        for x, y in coords:
            key = (round(x / grid_m), round(y / grid_m))
            grid[key].append({"x": x, "y": y, "nombre": nombre})

    # 2. Solo grupos con ≥ 3 endpoints (intersección real, no final de calle)
    inter_utm: list[dict] = []
    for pts in grid.values():
        if len(pts) < 3:
            continue
        cx = sum(p["x"] for p in pts) / len(pts)
        cy = sum(p["y"] for p in pts) / len(pts)
        nombres = sorted({p["nombre"] for p in pts if p["nombre"]})
        inter_utm.append({"point_utm": Point(cx, cy), "calles": nombres})

    if not inter_utm:
        return []

    # 3. Convertir a WGS84
    inter_gdf = gpd.GeoDataFrame(
        [{"calles": d["calles"]} for d in inter_utm],
        geometry=[d["point_utm"] for d in inter_utm],
        crs=CRS_METRIC,
    ).to_crs(CRS_GEO)

    # 4. Contar incidentes cercanos (radio 80m) usando buffer pequeño
    inter_utm_gdf = inter_gdf.to_crs(CRS_METRIC)
    radios_utm = inter_utm_gdf.geometry.buffer(_RADIO_INTER_M)
    radios_geo = gpd.GeoDataFrame(geometry=radios_utm, crs=CRS_METRIC).to_crs(CRS_GEO).geometry

    # Preparar índice espacial de puntos de incidentes
    todos_incidentes = gpd.GeoDataFrame()
    for df in [hechos, incidentes]:
        if df is not None and not df.empty and "geometry" in df.columns:
            todos_incidentes = pd.concat([todos_incidentes, df[["geometry"]]])

    resultado = []
    for i, (_, row) in enumerate(inter_gdf.iterrows()):
        n_inc = 0
        if not todos_incidentes.empty:
            radio = radios_geo.iloc[i]
            try:
                n_inc = todos_incidentes[todos_incidentes.geometry.within(radio)].shape[0]
            except Exception:
                pass

        nivel = "alto" if n_inc >= 5 else "medio" if n_inc >= 2 else "bajo"
        resultado.append({
            "lat":          row.geometry.y,
            "lng":          row.geometry.x,
            "n_incidentes": n_inc,
            "calles":       " / ".join(row["calles"][:2]) if row["calles"] else "Intersección",
            "nivel_riesgo": nivel,
        })

    return sorted(resultado, key=lambda x: x["n_incidentes"], reverse=True)


# ── Función pública de análisis (firma sin cambios) ───────────────────────────

def analyze_movilidad(
    lat: float,
    lng: float,
    layers: dict,
    alcaldia: str = "",
) -> tuple[dict, dict]:
    fc = _filtrar_capas(lat, lng, layers, alcaldia)
    hechos, incidentes = fc["hechos"], fc["incidentes"]

    intersecciones_txt = _intersecciones_por_nombres(hechos, incidentes)
    tipo_frec  = _tipo_frecuente(hechos, incidentes)
    densidad   = (len(hechos) + len(incidentes)) / BUFFER_AREA_KM2

    metrics = {
        "n_hechos_transito":       len(hechos),
        "n_incidentes_c5":         len(incidentes),
        "n_infracciones_alcaldia": len(fc["infracciones"]),
        "intersecciones_riesgo":   intersecciones_txt,
        "densidad_incidentes":     round(densidad, 2),
        "tipo_incidente_frecuente": tipo_frec,
    }

    matched_layers, findings = [], []
    if len(hechos) > 0:
        matched_layers.append("Hechos de Tránsito 2023")
        findings.append(f"{len(hechos)} hecho(s) de tránsito en 500 m.")
    if len(incidentes) > 0:
        matched_layers.append("Incidentes Viales C5")
        findings.append(f"{len(incidentes)} incidente(s) viales al C5 en el área.")
    if intersecciones_txt:
        matched_layers.append("Intersecciones de Alto Riesgo")
        findings.append(f"Intersecciones: {', '.join(intersecciones_txt[:3])}.")
    if tipo_frec != "sin datos":
        findings.append(f"Incidente más frecuente: {tipo_frec}.")
    findings.append(f"Densidad: {densidad:.1f} eventos/km².")
    if len(fc["infracciones"]) > 0:
        matched_layers.append("Infracciones al Reglamento")
        findings.append(f"{len(fc['infracciones'])} infracción(es) en la alcaldía {alcaldia}.")
    if not matched_layers:
        findings.append("Sin incidentes viales en el radio de 500 m.")

    return metrics, {"matched_layers": matched_layers, "findings": findings}


# ── Generación de mapas ───────────────────────────────────────────────────────

_COLOR_RIESGO = {"alto": "#C0392B", "medio": "#E67E22", "bajo": "#2980B9"}


def _add_intersecciones_capa(
    m: folium.Map,
    inter_data: list[dict],
    show: bool = True,
    max_inter: int = 50,
):
    """
    Agrega un FeatureGroup con las intersecciones de la red vial al mapa.
    El color y tamaño del marcador refleja el nivel de riesgo:
      - Rojo   (#C0392B): alto  (≥ 5 incidentes)
      - Naranja (#E67E22): medio (2-4 incidentes)
      - Azul   (#2980B9): bajo  (< 2 incidentes)
    """
    if not inter_data:
        return
    grupo = folium.FeatureGroup(name="Intersecciones detectadas", show=show)
    for inter in inter_data[:max_inter]:
        color = _COLOR_RIESGO[inter["nivel_riesgo"]]
        size  = 5 + min(inter["n_incidentes"], 5)   # 5–10 px de brazo
        thick = 2                                         # grosor fijo 2 px
        html  = (
            f'<div style="position:relative;width:{size*2}px;height:{size*2}px">'
            # barra horizontal
            f'<div style="position:absolute;top:50%;left:0;transform:translateY(-50%);'
            f'width:100%;height:{thick}px;background:{color};border-radius:2px"></div>'
            # barra vertical
            f'<div style="position:absolute;left:50%;top:0;transform:translateX(-50%);'
            f'width:{thick}px;height:100%;background:{color};border-radius:2px"></div>'
            f'</div>'
        )
        folium.Marker(
            [inter["lat"], inter["lng"]],
            tooltip=(
                f"🔀 <b>{inter['calles']}</b><br>"
                f"Incidentes cercanos: <b>{inter['n_incidentes']}</b><br>"
                f"Nivel de riesgo: <b>{inter['nivel_riesgo'].upper()}</b>"
            ),
            icon=folium.DivIcon(
                html=html,
                icon_size=(size * 2, size * 2),
                icon_anchor=(size, size),
            ),
        ).add_to(grupo)
    grupo.add_to(m)


def _base_map(lat: float, lng: float) -> folium.Map:
    m = folium.Map(
        location=[lat, lng], zoom_start=15,
        tiles="CartoDB positron", control_scale=True,
    )
    folium.Circle(
        [lat, lng], radius=BUFFER_RADIUS_M,
        color="#2D5A3D", weight=2, dash_array="8 4",
        fill=True, fill_color="#2D5A3D", fill_opacity=0.04,
        tooltip="Radio de análisis: 500 m",
    ).add_to(m)
    folium.Marker(
        [lat, lng], tooltip="📍 Punto del reporte",
        icon=folium.Icon(color="red", icon="exclamation-sign", prefix="glyphicon"),
    ).add_to(m)
    return m


def mapas_movilidad(
    lat: float,
    lng: float,
    layers: dict,
    alcaldia: str = "",
) -> dict[str, folium.Map]:
    """
    Genera tres mapas folium para el análisis de movilidad:
      - 'heatmap':        Mapa de calor de densidad de incidentes
      - 'puntos':         Puntos individuales con popups informativos
      - 'intersecciones': Red vial con intersecciones coloreadas por nivel de riesgo
    """
    fc = _filtrar_capas(lat, lng, layers, alcaldia)
    hechos, incidentes, calles = fc["hechos"], fc["incidentes"], fc["calles"]

    # Detectar intersecciones de la red vial
    inter_data = detectar_intersecciones_red_vial(calles, hechos, incidentes)

    # ── Mapa 1: Mapa de calor ─────────────────────────────────────────────────
    m_heat = _base_map(lat, lng)

    heat_pts = []
    for df, peso in [(hechos, 1.0), (incidentes, 0.6)]:
        if df.empty:
            continue
        for _, row in df.iterrows():
            if row.geometry:
                heat_pts.append([row.geometry.y, row.geometry.x, peso])

    if heat_pts:
        folium.plugins.HeatMap(
            heat_pts,
            name="Densidad de incidentes",
            min_opacity=0.3,
            radius=18,
            blur=20,
            gradient={0.2: "#FEF9E7", 0.5: "#F39C12", 0.75: "#C0392B", 1.0: "#7B0000"},
        ).add_to(m_heat)

    # Intersecciones encima del heatmap
    _add_intersecciones_capa(m_heat, inter_data, show=True)

    _leyenda_heatmap(m_heat)
    folium.LayerControl().add_to(m_heat)

    # ── Mapa 2: Puntos individuales ───────────────────────────────────────────
    m_puntos = _base_map(lat, lng)

    grupo_h = folium.FeatureGroup(name="Hechos de tránsito", show=True)
    for _, row in hechos.iterrows():
        if row.geometry is None:
            continue
        tipo  = row.get("tipo_evento", "N/D")
        fecha = row.get("fecha_evento", "N/D")
        pri   = row.get("prioridad", "")
        fallecidos = row.get("personas_fallecidas", 0)
        lesionados = row.get("personas_lesionadas", 0)
        color = "#C0392B" if str(pri).upper() == "ALTA" else "#E67E22"
        radio = 8 if fallecidos and int(fallecidos) > 0 else 5
        folium.CircleMarker(
            [row.geometry.y, row.geometry.x],
            radius=radio, color=color, fill=True,
            fill_color=color, fill_opacity=0.8, weight=1.5,
            tooltip=(f"🚨 <b>{tipo}</b><br>"
                     f"Fecha: {fecha}<br>"
                     f"Fallecidos: {fallecidos} | Lesionados: {lesionados}"),
        ).add_to(grupo_h)
    grupo_h.add_to(m_puntos)

    grupo_c5 = folium.FeatureGroup(name="Incidentes C5", show=True)
    for _, row in incidentes.iterrows():
        if row.geometry is None:
            continue
        tipo = row.get("tipo_incidente_c4", row.get("incidente_c4", "N/D"))
        hora = row.get("hora_creacion", "N/D")
        folium.CircleMarker(
            [row.geometry.y, row.geometry.x],
            radius=5, color="#7D3C98", fill=True,
            fill_color="#A569BD", fill_opacity=0.7, weight=1,
            tooltip=f"📞 <b>C5: {tipo}</b><br>Hora: {hora}",
        ).add_to(grupo_c5)
    grupo_c5.add_to(m_puntos)

    # Intersecciones encima de los puntos
    _add_intersecciones_capa(m_puntos, inter_data, show=True)

    _leyenda_puntos(m_puntos)
    folium.LayerControl().add_to(m_puntos)

    # ── Mapa 3: Red vial + intersecciones ─────────────────────────────────────
    m_inter = _base_map(lat, lng)

    # Dibujar segmentos de calle
    if not calles.empty:
        grupo_calles = folium.FeatureGroup(name="Red vial", show=True)
        for _, row in calles.iterrows():
            if row.geometry is None:
                continue
            nombre = row.get("nom_vialid", "")
            tipo   = row.get("tipo_viali", "")
            try:
                _add_linestring(grupo_calles, row.geometry, nombre, tipo)
            except Exception:
                pass
        grupo_calles.add_to(m_inter)

    # Dibujar puntos de incidentes pequeños como contexto
    grupo_inc_ctx = folium.FeatureGroup(name="Incidentes (contexto)", show=False)
    for df, color_inc in [(hechos, "#E74C3C"), (incidentes, "#9B59B6")]:
        for _, row in df.iterrows():
            if row.geometry:
                folium.CircleMarker(
                    [row.geometry.y, row.geometry.x],
                    radius=3, color=color_inc, fill=True,
                    fill_color=color_inc, fill_opacity=0.4, weight=0,
                ).add_to(grupo_inc_ctx)
    grupo_inc_ctx.add_to(m_inter)

    # Dibujar intersecciones (coloreadas por nivel de riesgo)
    _add_intersecciones_capa(m_inter, inter_data, show=True)

    _leyenda_intersecciones(m_inter, len(inter_data))
    folium.LayerControl().add_to(m_inter)

    return {"heatmap": m_heat, "puntos": m_puntos, "intersecciones": m_inter}


def _add_linestring(grupo, geom, nombre: str, tipo: str):
    """Agrega una LineString o MultiLineString al grupo."""
    grosor = 3 if "PRINCIPAL" in tipo.upper() or "EJE" in tipo.upper() else 1.5
    color  = "#5D6D7E" if "PRINCIPAL" in tipo.upper() else "#AAB7B8"

    if geom.geom_type == "LineString":
        coords = [[y, x] for x, y in geom.coords]
        folium.PolyLine(
            coords, color=color, weight=grosor, opacity=0.7,
            tooltip=nombre or "Calle sin nombre",
        ).add_to(grupo)
    elif geom.geom_type == "MultiLineString":
        for seg in geom.geoms:
            coords = [[y, x] for x, y in seg.coords]
            folium.PolyLine(coords, color=color, weight=grosor, opacity=0.7).add_to(grupo)


def _leyenda_heatmap(m: folium.Map):
    html = """
    <div style="position:fixed;bottom:30px;right:10px;z-index:9999;
                background:white;padding:12px 16px;border-radius:8px;
                box-shadow:2px 2px 6px rgba(0,0,0,.25);font-size:12px">
        <b>Densidad de incidentes</b>
        <div style="margin-top:8px;height:12px;width:140px;
                    background:linear-gradient(to right,#FEF9E7,#F39C12,#C0392B,#7B0000);
                    border-radius:4px"></div>
        <div style="display:flex;justify-content:space-between;
                    width:140px;font-size:10px;color:#888;margin-top:2px">
            <span>Baja</span><span>Alta</span>
        </div>
    </div>"""
    m.get_root().html.add_child(folium.Element(html))


def _leyenda_puntos(m: folium.Map):
    html = """
    <div style="position:fixed;bottom:30px;right:10px;z-index:9999;
                background:white;padding:12px 16px;border-radius:8px;
                box-shadow:2px 2px 6px rgba(0,0,0,.25);font-size:12px">
        <b>Fuente de datos</b>
        <ul style="list-style:none;padding:0;margin:8px 0 0 0">
            <li><span style="background:#E74C3C;display:inline-block;
                width:12px;height:12px;border-radius:50%;margin-right:6px"></span>Hecho de tránsito</li>
            <li><span style="background:#9B59B6;display:inline-block;
                width:12px;height:12px;border-radius:50%;margin-right:6px"></span>Incidente C5</li>
        </ul>
    </div>"""
    m.get_root().html.add_child(folium.Element(html))


def _leyenda_intersecciones(m: folium.Map, n_total: int):
    html = f"""
    <div style="position:fixed;bottom:30px;right:10px;z-index:9999;
                background:white;padding:12px 16px;border-radius:8px;
                box-shadow:2px 2px 6px rgba(0,0,0,.25);font-size:12px;min-width:170px">
        <b>Intersecciones detectadas</b>
        <div style="color:#888;font-size:11px;margin-bottom:8px">{n_total} en el área</div>
        <ul style="list-style:none;padding:0;margin:0">
            <li><span style="background:#C0392B;display:inline-block;
                width:12px;height:12px;border-radius:50%;margin-right:6px"></span>Alto riesgo (≥5 inc.)</li>
            <li><span style="background:#E67E22;display:inline-block;
                width:12px;height:12px;border-radius:50%;margin-right:6px"></span>Medio (2–4 inc.)</li>
            <li><span style="background:#2980B9;display:inline-block;
                width:12px;height:12px;border-radius:50%;margin-right:6px"></span>Bajo (&lt;2 inc.)</li>
        </ul>
        <div style="border-top:1px solid #eee;margin-top:8px;padding-top:6px;color:#888;font-size:11px">
            Tamaño del círculo ∝ incidentes cercanos
        </div>
    </div>"""
    m.get_root().html.add_child(folium.Element(html))
