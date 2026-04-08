"""
Interfaz Streamlit para probar el análisis espacial de SeñalCDMX.

Ejecutar desde la raíz del proyecto:
    streamlit run app/services/analysis/interfaz_probar_funciones.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[3]))

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="SeñalCDMX — Análisis Espacial",
    page_icon="📍",
    layout="wide",
)

# ── Datos de prueba ────────────────────────────────────────────────────────────
UBICACIONES = {
    "— Elegir ubicación —": None,
    "Iztapalapa — Zona de inundación":          (19.3724, -99.0633, "Iztapalapa"),
    "Tláhuac — Riesgo hídrico":                 (19.2900, -99.0050, "Tláhuac"),
    "Gustavo A. Madero — Encharcamiento":       (19.4850, -99.1100, "Gustavo A. Madero"),
    "Cuauhtémoc — Insurgentes / Reforma":       (19.4284, -99.1677, "Cuauhtémoc"),
    "Benito Juárez — Eje 7 / Antillas":        (19.3681, -99.1429, "Benito Juárez"),
    "Azcapotzalco — Cruce peatonal Vallejo":   (19.4870, -99.1850, "Azcapotzalco"),
}

EJEMPLOS = {
    "riesgos":   "Hay un encharcamiento enorme que no baja desde ayer, el agua llega a la rodilla y hay basura flotando. El drenaje está tapado.",
    "movilidad": "En la esquina hay muchos accidentes, los peatones no tienen tiempo de cruzar y los coches no respetan el semáforo.",
}

NIVEL_COLOR = {"alto": "#C0392B", "medio": "#E67E22", "bajo": "#2980B9", "ninguno": "#7F8C8D"}


# ── Cache de capas ─────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Cargando capas de datos abiertos CDMX…")
def _get_layers_fn():
    from app.services.layer_fetcher import load_all_layers, get_layers
    load_all_layers()
    return get_layers


# ── Helpers visuales ───────────────────────────────────────────────────────────
def _card(label, valor, unidad="", color="#2D5A3D", icono=""):
    st.markdown(
        f'<div style="background:#FAFAFA;border-left:5px solid {color};'
        f'padding:12px 16px;border-radius:8px;margin-bottom:4px">'
        f'<div style="font-size:10px;color:#888;text-transform:uppercase;'
        f'font-weight:700;letter-spacing:.7px">{label}</div>'
        f'<div style="font-size:24px;font-weight:800;color:{color};line-height:1.2">'
        f'{icono} {valor} <span style="font-size:12px;color:#999;font-weight:400">{unidad}</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _hallazgo(texto, tipo="info"):
    c = {"ok": "#27AE60", "warn": "#E67E22", "error": "#C0392B", "info": "#2980B9"}.get(tipo, "#2980B9")
    i = {"ok": "✅", "warn": "⚠️", "error": "🔴", "info": "📌"}.get(tipo, "📌")
    st.markdown(
        f'<div style="padding:8px 12px;border-radius:6px;margin-bottom:5px;'
        f'background:{c}15;border-left:3px solid {c};font-size:14px">{i} {texto}</div>',
        unsafe_allow_html=True,
    )


def _mapa_folium(m, height=460):
    """Renderiza un mapa folium dentro de Streamlit sin paquetes extra."""
    components.html(m._repr_html_(), height=height, scrolling=False)


def _mapa_preview(lat, lng):
    """Mapa de ubicación reactivo — se actualiza con cada cambio de coordenadas."""
    import folium
    m = folium.Map(location=[lat, lng], zoom_start=14, tiles="CartoDB positron")
    folium.Circle(
        [lat, lng], radius=500,
        color="#2D5A3D", weight=2, dash_array="8 4",
        fill=True, fill_color="#2D5A3D", fill_opacity=0.1,
        tooltip="Radio de análisis: 500 m",
    ).add_to(m)
    folium.Marker(
        [lat, lng],
        tooltip=f"📍 ({lat:.5f}, {lng:.5f})",
        icon=folium.Icon(color="red", icon="exclamation-sign", prefix="glyphicon"),
    ).add_to(m)
    components.html(m._repr_html_(), height=350, scrolling=False)


# ── Sección de resultados ──────────────────────────────────────────────────────
def _mostrar_metricas_riesgos(metrics):
    nivel = metrics.get("nivel_riesgo", "ninguno")
    color = NIVEL_COLOR.get(nivel, "#7F8C8D")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        en_zona = metrics.get("zona_riesgo_inundacion", False)
        _card("Zona de inundación", "Sí" if en_zona else "No",
              color="#C0392B" if en_zona else "#27AE60", icono="⚠️" if en_zona else "✅")
    with c2:
        _card("Nivel de riesgo", nivel.capitalize(), color=color, icono="🌊")
    with c3:
        _card("Tiraderos", metrics.get("n_tiraderos", 0), "en 500m", "#8E44AD", "🗑️")
    with c4:
        _card("Captación pluvial", metrics.get("n_puntos_captacion", 0), "en 500m", "#2980B9", "💧")

    c5, c6 = st.columns(2)
    with c5:
        av = metrics.get("cobertura_areas_verdes_m2", 0)
        deficit = metrics.get("deficit_areas_verdes", False)
        _card("Áreas verdes en buffer", f"{av:,.0f}", "m²",
              "#E67E22" if deficit else "#27AE60", "🌳")
        if deficit:
            st.warning("Déficit de áreas verdes detectado")
        else:
            st.success("Cobertura de áreas verdes adecuada")
    with c6:
        datos = pd.DataFrame({
            "Capa": ["Tiraderos", "Captación", "Presas"],
            "Registros": [metrics.get("n_tiraderos", 0),
                          metrics.get("n_puntos_captacion", 0),
                          metrics.get("n_presas_cercanas", 0)],
        })
        st.markdown("**Registros en buffer de 500m**")
        st.bar_chart(datos.set_index("Capa"), color="#2D5A3D", height=180)


def _mostrar_metricas_movilidad(metrics):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _card("Hechos de tránsito", metrics.get("n_hechos_transito", 0), "en 500m", "#C0392B", "🚨")
    with c2:
        _card("Incidentes C5", metrics.get("n_incidentes_c5", 0), "en 500m", "#E67E22", "📞")
    with c3:
        _card("Densidad", f"{metrics.get('densidad_incidentes', 0):.1f}", "ev/km²", "#8E44AD", "📊")
    with c4:
        _card("Infracciones (alcaldía)", metrics.get("n_infracciones_alcaldia", 0),
              "registros", "#2980B9", "📋")

    c5, c6 = st.columns(2)
    with c5:
        tipo = metrics.get("tipo_incidente_frecuente", "sin datos")
        st.markdown(
            f'<div style="background:#FEF9E7;border-left:5px solid #E67E22;'
            f'padding:14px;border-radius:8px"><div style="font-size:10px;color:#888;'
            f'text-transform:uppercase;font-weight:700">Incidente más frecuente</div>'
            f'<div style="font-size:20px;font-weight:800;color:#E67E22;margin-top:4px">'
            f'🚗 {tipo.replace("_", " ").capitalize()}</div></div>',
            unsafe_allow_html=True,
        )
    with c6:
        datos = pd.DataFrame({
            "Fuente": ["Hechos tránsito", "Incidentes C5"],
            "Registros": [metrics.get("n_hechos_transito", 0),
                          metrics.get("n_incidentes_c5", 0)],
        })
        st.markdown("**Registros por fuente**")
        st.bar_chart(datos.set_index("Fuente"), color="#C0392B", height=180)


def _mostrar_hallazgos(layers_summary):
    matched = layers_summary.get("matched_layers", [])
    findings = layers_summary.get("findings", [])
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.markdown("**Capas con coincidencias**")
        for c in matched:
            st.markdown(f"✅ {c}")
        if not matched:
            st.markdown("_Sin coincidencias_")
    with col_b:
        st.markdown("**Detalle de hallazgos**")
        for f in findings:
            tipo = ("error" if any(k in f.lower() for k in ["alto", "urgente", "grave"])
                    else "warn" if any(k in f.lower() for k in ["déficit", "tiradero", "hecho", "incidente"])
                    else "ok" if "adecuada" in f.lower()
                    else "info")
            _hallazgo(f, tipo)


# ── App principal ──────────────────────────────────────────────────────────────
def main():
    st.markdown(
        '<h1 style="color:#2D5A3D;margin-bottom:0">📍 SeñalCDMX — Análisis Espacial</h1>'
        '<p style="color:#6C757D;font-size:15px;margin-top:4px">'
        'Simula los datos de <b>ubicación del frontend</b> y la <b>categoría del LLM</b>. '
        'Ejecuta el análisis geoespacial y visualiza los resultados en mapas interactivos.</p>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # ── Sidebar ────────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Parámetros de entrada")
        st.markdown("#### 📍 Ubicación")
        preset = st.selectbox("Ubicación de prueba", list(UBICACIONES.keys()))
        pval   = UBICACIONES[preset]

        manual = st.checkbox("Coordenadas manuales", value=pval is None)
        if manual or pval is None:
            lat      = st.number_input("Latitud",   value=19.4326, format="%.6f", step=0.0001)
            lng      = st.number_input("Longitud",  value=-99.1332, format="%.6f", step=0.0001)
            alcaldia = st.text_input("Alcaldía",   value="Cuauhtémoc")
        else:
            lat, lng, alcaldia = pval
            st.success(f"**{alcaldia}**\nLat: `{lat}` Lng: `{lng}`")

        st.markdown("---")
        st.markdown("#### 🤖 Categoría del LLM")
        categoria = st.radio(
            "Categoría detectada",
            ["riesgos", "movilidad"],
            captions=["Inundaciones · Drenaje · Riesgo natural",
                      "Accidentes · Baches · Cruces peligrosos"],
        )

        st.markdown("---")
        ejecutar = st.button("▶️ Ejecutar análisis", type="primary", use_container_width=True)

    # ── Panel previo a ejecución ───────────────────────────────────────────────
    col_mapa, col_info = st.columns([3, 2])
    with col_mapa:
        st.markdown("#### 🗺️ Ubicación seleccionada (buffer 500m)")
        _mapa_preview(lat, lng)
    with col_info:
        st.markdown("#### 📝 Descripción de prueba")
        st.text_area("", value=EJEMPLOS[categoria], height=110,
                     label_visibility="collapsed", key="desc")
        st.markdown("#### 🧭 Punto de análisis")
        st.table(pd.DataFrame({
            "Campo": ["Latitud", "Longitud", "Alcaldía", "Categoría LLM", "Radio"],
            "Valor": [f"{lat}", f"{lng}", alcaldia, categoria, "500 m"],
        }).set_index("Campo"))

    # ── Resultados ─────────────────────────────────────────────────────────────
    if not ejecutar:
        st.info("👈 Configura los parámetros y presiona **▶️ Ejecutar análisis**.")
        return

    get_layers_fn = _get_layers_fn()
    layers = get_layers_fn(categoria)

    with st.spinner("Ejecutando análisis espacial…"):
        from app.services.spatial import spatial_analysis
        metrics, layers_summary = spatial_analysis(
            lat=lat, lng=lng, category=categoria,
            layers=layers, alcaldia=alcaldia,
        )

    with st.spinner("Generando mapas…"):
        if categoria == "riesgos":
            from app.services.analysis.riesgos import mapas_riesgos
            mapas = mapas_riesgos(lat, lng, layers)
        else:
            from app.services.analysis.movilidad import mapas_movilidad
            mapas = mapas_movilidad(lat, lng, layers, alcaldia)

    # Banner de estado
    matched_n = len(layers_summary.get("matched_layers", []))
    c1, c2, c3 = st.columns(3)
    c1.success("✅ Análisis completado")
    c2.info(f"📂 {matched_n} capa(s) con coincidencias")
    c3.info(f"📍 ({lat:.5f}, {lng:.5f})")

    st.markdown("---")

    # ── Métricas ───────────────────────────────────────────────────────────────
    st.markdown("## 📊 Métricas")
    if categoria == "riesgos":
        _mostrar_metricas_riesgos(metrics)
    else:
        _mostrar_metricas_movilidad(metrics)

    st.markdown("---")

    # ── Hallazgos ──────────────────────────────────────────────────────────────
    st.markdown("## 🔍 Hallazgos geoespaciales")
    _mostrar_hallazgos(layers_summary)

    st.markdown("---")

    # ── Mapas ──────────────────────────────────────────────────────────────────
    st.markdown("## 🗺️ Mapas interactivos")

    if categoria == "riesgos":
        tab1, tab2, tab3 = st.tabs([
            "🌊 Atlas de Riesgo Hídrico",
            "🏗️ Infraestructura (Tiraderos · Captación · Áreas verdes)",
            "🗺️ Vista general",
        ])
        with tab1:
            st.caption("Polígonos del Atlas de Riesgo de Inundaciones y Niveles de Inundación por colonia. "
                       "Color: intensidad del riesgo (rojo oscuro = Muy Alto).")
            _mapa_folium(mapas["atlas"], height=500)
        with tab2:
            st.caption("Tiraderos clandestinos (morado), puntos de captación pluvial (azul) "
                       "y áreas verdes (verde) dentro del buffer de 500m.")
            _mapa_folium(mapas["infraestructura"], height=500)
        with tab3:
            st.caption("Vista consolidada de todas las capas de riesgo en el área de análisis.")
            _mapa_folium(mapas["general"], height=500)

    else:
        tab1, tab2, tab3 = st.tabs([
            "🔥 Mapa de calor de incidentes",
            "📍 Incidentes individuales",
            "🔀 Red vial e intersecciones",
        ])
        with tab1:
            st.caption("Densidad de hechos de tránsito (2023) e incidentes reportados al C5. "
                       "Rojo oscuro = mayor concentración.")
            _mapa_folium(mapas["heatmap"], height=500)
        with tab2:
            st.caption("Cada punto es un evento registrado. "
                       "Rojo = hecho de tránsito (tamaño mayor si hay fallecidos). "
                       "Morado = incidente C5. Haz clic para ver detalles.")
            _mapa_folium(mapas["puntos"], height=500)
        with tab3:
            st.caption("Red vial dentro del área de análisis. "
                       "Los círculos son intersecciones detectadas: "
                       "tamaño y color indican nivel de riesgo según incidentes cercanos (radio 80m). "
                       "⚠️ = intersecciones de mayor riesgo.")
            _mapa_folium(mapas["intersecciones"], height=500)

    # Tabla de intersecciones (solo movilidad)
    if categoria == "movilidad":
        st.markdown("---")
        st.markdown("## 🔀 Intersecciones detectadas en el área")
        st.caption("Intersecciones de la red vial dentro del buffer, ordenadas por número de incidentes cercanos.")

        from app.services.analysis.movilidad import (
            _filtrar_capas, detectar_intersecciones_red_vial,
        )
        with st.spinner("Calculando intersecciones…"):
            fc = _filtrar_capas(lat, lng, layers, alcaldia)
            inter_data = detectar_intersecciones_red_vial(
                fc["calles"], fc["hechos"], fc["incidentes"]
            )

        if inter_data:
            df_inter = pd.DataFrame(inter_data)[["calles", "n_incidentes", "nivel_riesgo", "lat", "lng"]]
            df_inter.columns = ["Calles", "Incidentes cercanos", "Nivel de riesgo", "Lat", "Lng"]
            df_inter["Lat"] = df_inter["Lat"].round(5)
            df_inter["Lng"] = df_inter["Lng"].round(5)

            def _color_nivel(val):
                c = {"alto": "#FBEAE8", "medio": "#FEF9E7", "bajo": "#EAF4FB"}.get(val, "")
                return f"background-color: {c}" if c else ""

            st.dataframe(
                df_inter.style.applymap(_color_nivel, subset=["Nivel de riesgo"]),
                use_container_width=True,
                height=min(400, 40 + len(df_inter) * 35),
            )
            st.caption(f"Total: {len(inter_data)} intersecciones detectadas en el buffer.")
        else:
            st.info("No se detectaron intersecciones con suficientes puntos de convergencia en el área.")

    # JSON raw
    with st.expander("🔍 Datos crudos (JSON)"):
        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**metrics**")
            st.json(metrics)
        with cc2:
            st.markdown("**layers_summary**")
            st.json(layers_summary)


if __name__ == "__main__":
    main()
