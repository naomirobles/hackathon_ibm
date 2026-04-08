"""Vista raíz del ciudadano."""
import dash
from dash import html, dcc, Input, Output, State, callback, ctx
import dash
from dash import html, dcc, Input, Output, State, callback, clientside_callback
from componentes.navegacion import navbar
from vistas.nuevo_reporte import layout_nuevo
from vistas.mis_reportes import layout_mis


def layout_ciudadano(usuario: str = "Ana García") -> html.Div:
    return html.Div([
        navbar(role="ciudadano", usuario=usuario),
        html.Div(className="main", children=[
            html.Div(layout_nuevo(), id="panel-ciudadano-nuevo"),
            html.Div(layout_mis(),   id="panel-ciudadano-mis",
                     style={"display": "none"}),
        ]),
    ])


# Navegación entre paneles 

@callback(
    Output("panel-ciudadano-nuevo", "style"),
    Output("panel-ciudadano-mis",   "style"),
    Output("tab-nuevo", "className"),
    Output("tab-mis",   "className"),
    Input("tab-nuevo",    "n_clicks"),
    Input("tab-mis",      "n_clicks"),
    Input("btn-ir-nuevo", "n_clicks"),
    prevent_initial_call=True,
)
def switch_panel(n_nuevo, n_mis, n_ir_nuevo):
    show, hide = {}, {"display": "none"}
    active, normal = "nav-tab active", "nav-tab"
    if ctx.triggered_id == "tab-mis":
        return hide, show, normal, active
    return show, hide, active, normal


# Mapa → lat/lon: el postMessage del iframe actualiza el store,
# y este callback propaga los valores a los inputs de Dash.
clientside_callback(
    """
    function(paso) {
        if (!window._dashMapListenerSet) {
            window.addEventListener('message', function(e) {
                if (!e.data || e.data.type !== 'MAP_CLICK') return;
                var lat = e.data.lat;
                var lng = e.data.lng;

                // Helper: actualiza un input controlado por React
                var setter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value').set;
                function setInput(el, val) {
                    if (!el) return;
                    setter.call(el, val);
                    el.dispatchEvent(new Event('input',  {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                }

                // 1) Lat / Lon
                setInput(document.getElementById('lat-input'), lat.toFixed(6));
                setInput(document.getElementById('lon-input'), lng.toFixed(6));

                // 2) Dirección aproximada via Nominatim (reverse geocoding)
                var dirEl = document.getElementById('dir-input');
                if (dirEl) {
                    setInput(dirEl, 'Obteniendo dirección…');
                    fetch(
                        'https://nominatim.openstreetmap.org/reverse'
                        + '?format=jsonv2'
                        + '&lat=' + lat
                        + '&lon=' + lng
                        + '&accept-language=es',
                        { headers: { 'Accept-Language': 'es' } }
                    )
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        var a = data.address || {};
                        var parts = [
                            a.road || a.pedestrian || a.footway || '',
                            a.suburb || a.neighbourhood || a.quarter || '',
                            a.city_district || a.borough || '',
                            a.city || a.town || a.village || '',
                            a.state || ''
                        ].filter(Boolean);
                        var dir = parts.length ? parts.join(', ') : (data.display_name || '');
                        setInput(dirEl, dir);
                    })
                    .catch(function() {
                        setInput(dirEl, lat.toFixed(5) + ', ' + lng.toFixed(5));
                    });
                }
            });
            window._dashMapListenerSet = true;
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("store-mapa-coords", "data"),
    Input("store-paso-actual",  "data"),
    prevent_initial_call=False,
)


# Tabs texto / audio 
@callback(
    Output("tab-content-texto", "style"),
    Output("tab-content-audio", "style"),
    Output("tab-btn-texto",     "className"),
    Output("tab-btn-audio",     "className"),
    Input("tab-btn-texto", "n_clicks"),
    Input("tab-btn-audio", "n_clicks"),
    prevent_initial_call=True,
)
def switch_input_tab(n_texto, n_audio):
    show, hide = {}, {"display": "none"}
    active, normal = "tab-btn active", "tab-btn"
    if ctx.triggered_id == "tab-btn-audio":
        return hide, show, normal, active
    return show, hide, active, normal


#  Grabación simulada (solo clicks, sin Interval) 
@callback(
    Output("audio-btn",             "className"),
    Output("audio-btn",             "children"),
    Output("audio-status",          "children"),
    Output("audio-timer",           "children"),
    Output("audio-transcript-wrap", "style"),
    Output("audio-transcript",      "children"),
    Output("store-grabando",        "data"),
    Input("audio-btn",      "n_clicks"),
    State("store-grabando", "data"),
    prevent_initial_call=True,
)
def toggle_audio(n_clicks, grabando):
    TRANSCRIPCION = (
        "Hay un bache muy profundo en la esquina de Insurgentes y Viaducto, "
        "justo frente a la farmacia. Lleva semanas sin atención y ya dañó "
        "la llanta de mi carro. Es urgente que lo reparen."
    )
    if not grabando:
        return "audio-btn recording", "Detener", \
               "Grabando… presiona para detener", "● REC", \
               {"display": "none"}, "", True
    else:
        return "audio-btn", "Grabar", \
               "Audio procesado correctamente", "0:08", \
               {}, TRANSCRIPCION, False


#  Navegación del formulario de pasos 
@callback(
    Output("form-step-1", "style"),
    Output("form-step-2", "style"),
    Output("form-step-3", "style"),
    Output("form-step-4", "style"),
    Output("store-paso-actual", "data"),
    Input("btn-paso-2",        "n_clicks"),
    Input("btn-paso-1-back",   "n_clicks"),
    Input("btn-paso-3",        "n_clicks"),
    Input("ai-interval",       "n_intervals"),
    State("store-paso-actual", "data"),
    prevent_initial_call=True,
)
def navegar_pasos(n2, n1back, n3, n_intervals, paso):
    show, hide = {}, {"display": "none"}
    t = ctx.triggered_id
    if   t == "btn-paso-2"    and paso == 1: paso = 2
    elif t == "btn-paso-1-back" and paso == 2: paso = 1
    elif t == "btn-paso-3"    and paso == 2: paso = 3
    elif t == "ai-interval"   and (n_intervals or 0) >= 7 and paso == 3: paso = 4
    return (
        show if paso == 1 else hide,
        show if paso == 2 else hide,
        show if paso == 3 else hide,
        show if paso == 4 else hide,
        paso,
    )


# ── Intervalo IA ──────────────────────────────────────────────────────────────

@callback(
    Output("ai-interval", "disabled"),
    Input("store-paso-actual", "data"),
)
def toggle_interval(paso):
    return paso != 3


@callback(
    Output("ai-s0", "className"), Output("ai-s1", "className"),
    Output("ai-s2", "className"), Output("ai-s3", "className"),
    Output("ai-s4", "className"), Output("ai-s5", "className"),
    Output("ai-s6", "className"),
    Input("ai-interval", "n_intervals"),
)
def update_ai_steps(n):
    n = n or 0
    return [
        "ai-step done" if i < n else ("ai-step active" if i == n else "ai-step")
        for i in range(7)
    ]


#  Galería de capturas 
@callback(
    Output("capturas-galeria",  "children"),
    Output("capturas-contador", "children"),
    Output("store-capturas",    "data"),
    Input("upload-imagen",  "contents"),
    State("upload-imagen",  "filename"),
    State("store-capturas", "data"),
    prevent_initial_call=True,
)
def agregar_capturas(contents_list, filenames, capturas_actuales):
    if not contents_list:
        return [], "", capturas_actuales or []
    capturas = list(capturas_actuales or [])
    if isinstance(contents_list, str):
        contents_list, filenames = [contents_list], [filenames]
    for content, filename in zip(contents_list, filenames):
        capturas.append({"content": content, "filename": filename, "status": "pendiente"})
    thumbs = [
        html.Div([
            html.Img(src=cap["content"],
                     style={"width": "100%", "height": "100%", "objectFit": "cover"}),
            html.Span(" Pendiente", className="badge badge-pendiente captura-badge"),
        ], className="captura-thumb pendiente", title=cap["filename"])
        for cap in capturas
    ]
    total = len(capturas)
    return (
        html.Div(thumbs, className="capturas-grid"),
        f"{total} captura{'s' if total != 1 else ''} adjunta{'s' if total != 1 else ''} · se procesarán al enviar",
        capturas,
    )


#  Step indicator ──────────────────────────────────────────────────────────────

@callback(
    Output("step-indicator", "children"),
    Input("store-paso-actual", "data"),
)
def actualizar_step_indicator(paso):
    paso = paso or 1

    def _step(num: int, label: str):
        if num < paso:
            estado = "done"
        elif num == paso:
            estado = "active"
        else:
            estado = ""
        return html.Div([
            html.Div(
                "✓" if num < paso else str(num),
                className="step-num",
            ),
            html.Div(label, className="step-label"),
        ], className=f"step {estado}".strip())

    return [
        _step(1, "Descripción"),
        _step(2, "Ubicación"),
        _step(3, "Análisis IA"),
        _step(4, "Resultado"),
    ]


#  Resultado de IA 

@callback(
    Output("result-card", "children"),
    Input("store-paso-actual", "data"),
    State("store-capturas",    "data"),
    prevent_initial_call=True,
)
def mostrar_resultado(paso, capturas):
    if paso != 4:
        return []
    import random
    rpt_id = f"RPT-{random.randint(100, 999)}"
    n_cap = len(capturas) if capturas else 0
    return [
        html.Div([
            html.Div([
                html.Div("Análisis completado",
                         style={"fontSize": "20px", "fontWeight": "600", "marginBottom": "8px"}),
                html.Div([
                    html.Span("Prioridad alta",  className="badge badge-alta"),
                    html.Span("Infraestructura", className="badge badge-cat"),
                    html.Span("Bache vial",      className="badge badge-info"),
                ], style={"display": "flex", "gap": "8px", "flexWrap": "wrap", "marginBottom": "8px"}),
                html.Div(f"ID: {rpt_id} · Confianza IA: 89% · {n_cap} captura{'s' if n_cap != 1 else ''} procesada{'s' if n_cap != 1 else ''}",
                         className="text-small"),
            ]),
            html.Div([
                html.Div("87%", className="priority-pct alta"),
                html.Div("prob. de atención", className="text-small"),
            ], style={"textAlign": "right"}),
        ], className="result-header"),

        html.Div([html.Strong("Análisis del sistema: "),
                  "El reporte describe una afectación vial de alta peligrosidad. "
                  "La zona registra densidad vehicular elevada."],
                 className="ai-analysis-box"),

        html.Div([
            html.Div([html.Div("Categoría", className="info-item-label"),
                      html.Div("Infraestructura", className="info-item-value")], className="info-item"),
            html.Div([html.Div("Tipo", className="info-item-label"),
                      html.Div("Bache vial", className="info-item-value")], className="info-item"),
            html.Div([html.Div("Confianza IA", className="info-item-label"),
                      html.Div("89%", className="info-item-value")], className="info-item"),
        ], className="info-grid"),

        *([html.Div([
            html.Div("Evidencia fotográfica procesada",
                     style={"fontSize": "12px", "fontWeight": "600", "color": "var(--text2)",
                            "marginBottom": "8px", "textTransform": "uppercase"}),
            html.Div([
                html.Div([
                    html.Img(src=cap["content"],
                             style={"width": "100%", "height": "100%", "objectFit": "cover"}),
                    html.Span("✓ OK", className="badge badge-baja captura-badge"),
                ], className="captura-thumb") for cap in capturas
            ], className="capturas-grid"),
        ], style={"marginBottom": "16px"})] if capturas else []),

        html.Div([
            html.Span("✓", style={"fontSize": "14px", "flexShrink": "0"}),
            html.Div([html.Strong("Recomendación: "),
                      "Se recomienda enviar brigada de mantenimiento en las próximas 48 horas."]),
        ], className="alert alert-success"),

        html.Div([
            html.Div("Documento técnico generado",
                     style={"fontSize": "13px", "fontWeight": "500",
                            "color": "var(--primary)", "marginBottom": "4px"}),
            html.Div(f"{rpt_id}_reporte_tecnico.pdf", className="text-small",
                     style={"marginBottom": "10px"}),
            html.Button("↓ Descargar PDF", className="btn btn-sm btn-outline",
                        style={"color": "var(--primary)", "borderColor": "var(--primary)"}),
        ], style={"background": "var(--primary-light)", "border": "1px solid rgba(15,143,74,0.2)",
                  "borderRadius": "var(--radius-sm)", "padding": "16px", "marginBottom": "16px"}),

        html.Div([
            html.Button("Crear nuevo reporte", id="btn-nuevo-reporte",
                        className="btn btn-outline", n_clicks=0),
            html.Button("Ver mis reportes", id="btn-ver-mis",
                        className="btn btn-primary", n_clicks=0),
        ], style={"display": "flex", "gap": "8px", "justifyContent": "flex-end",
                  "paddingTop": "16px", "borderTop": "1px solid var(--border)"}),
    ]
