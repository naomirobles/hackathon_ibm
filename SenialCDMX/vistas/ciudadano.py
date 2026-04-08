import dash
from dash import html, dcc, Input, Output, State, callback, clientside_callback
from componentes.navegacion import navbar
from vistas.nuevo_reporte import layout_nuevo
from vistas.mis_reportes import layout_mis


def layout_ciudadano(usuario: str = "Ana García") -> html.Div:
    return html.Div([
        navbar(role="ciudadano", usuario=usuario),
        html.Div(className="main", children=[
            html.Div(layout_nuevo(), id="panel-ciudadano-nuevo",
                     className="panel active"),
            html.Div(layout_mis(), id="panel-ciudadano-mis",
                     className="panel", style={"display": "none"}),
        ]),
    ])


# ── Navegación entre paneles ──────────────────────────────────────────────────

@callback(
    Output("panel-ciudadano-nuevo", "style"),
    Output("panel-ciudadano-mis",   "style"),
    Output("tab-nuevo", "className"),
    Output("tab-mis",   "className"),
    Input("tab-nuevo", "n_clicks"),
    Input("tab-mis",   "n_clicks"),
    prevent_initial_call=True,
)
def switch_panel_ciudadano(n_nuevo, n_mis):
    triggered = dash.ctx.triggered_id
    if triggered == "tab-mis":
        return {"display": "none"}, {}, "nav-tab", "nav-tab active"
    return {}, {"display": "none"}, "nav-tab active", "nav-tab"


# ── Step indicator ────────────────────────────────────────────────────────────

@callback(
    Output("step-indicator", "children"),
    Input("store-paso-actual", "data"),
)
def actualizar_step_indicator(paso):
    from vistas.nuevo_reporte import _step
    def estado(num):
        if num < paso:  return "done"
        if num == paso: return "active"
        return ""
    return [
        _step(1, "Descripción", estado(1)),
        _step(2, "Ubicación",   estado(2)),
        _step(3, "Análisis IA", estado(3)),
        _step(4, "Resultado",   estado(4)),
    ]


# ── Navegación entre pasos del formulario ────────────────────────────────────

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
    Input("store-paso-actual", "data"),
    prevent_initial_call=True,
)
def navegar_pasos(n2, n1back, n3, n_intervals, paso_actual):
    triggered = dash.ctx.triggered_id
    show, hide = {}, {"display": "none"}
    if triggered == "btn-paso-2"      and paso_actual == 1: paso = 2
    elif triggered == "btn-paso-1-back" and paso_actual == 2: paso = 1
    elif triggered == "btn-paso-3"    and paso_actual == 2: paso = 3
    elif triggered == "ai-interval"   and n_intervals >= 7 and paso_actual == 3: paso = 4
    else: paso = paso_actual
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
    return [
        "ai-step done" if i < n else ("ai-step active" if i == n else "ai-step")
        for i in range(7)
    ]


# ── Mapa: clientside_callback → postMessage del iframe → Store ───────────────
# Cada 300ms verifica si el iframe envió coordenadas nuevas via postMessage

clientside_callback(
    """
    function(_) {
        if (!window.__mapListenerSet) {
            window.__mapListenerSet = true;
            window.__mapCoords = null;
            window.addEventListener('message', function(e) {
                if (e.data && e.data.type === 'MAP_CLICK') {
                    window.__mapCoords = { lat: e.data.lat, lng: e.data.lng };
                }
            });
        }
        if (window.__mapCoords) {
            var c = window.__mapCoords;
            window.__mapCoords = null;
            return c;
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("store-mapa-coords", "data"),
    Input("mapa-poll-interval", "n_intervals"),
    prevent_initial_call=True,
)


# ── Mapa: Store → lat / lon / dirección (reverse geocoding Nominatim) ─────────

@callback(
    Output("lat-input",  "value"),
    Output("lon-input",  "value"),
    Output("dir-input",  "value"),
    Output("dir-status", "children"),
    Input("store-mapa-coords", "data"),
    prevent_initial_call=True,
)
def actualizar_ubicacion(coords):
    if not coords:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    lat = round(coords["lat"], 6)
    lng = round(coords["lng"], 6)

    import requests
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"format": "jsonv2", "lat": lat, "lon": lng},
            headers={"User-Agent": "SenialCDMX/1.0"},
            timeout=5,
        )
        data = resp.json()
        direccion = data.get("display_name", f"{lat}, {lng}")
        status = "✓ Dirección obtenida automáticamente"
    except Exception:
        direccion = f"{lat}, {lng}"
        status = "⚠ Sin conexión — mostrando coordenadas"

    return str(lat), str(lng), direccion, status


# ── Resultado del reporte ─────────────────────────────────────────────────────

@callback(
    Output("result-card", "children"),
    Input("store-paso-actual", "data"),
    prevent_initial_call=True,
)
def mostrar_resultado(paso):
    if paso != 4:
        return []
    import random
    rpt_id = f"RPT-{random.randint(100, 999)}"
    return [
        html.Div([
            html.Div([
                html.Div("Análisis completado",
                         style={"fontSize": "20px", "fontWeight": "600",
                                "marginBottom": "8px"}),
                html.Div([
                    html.Span("Prioridad alta", className="badge badge-alta"),
                    html.Span("Infraestructura", className="badge badge-cat"),
                    html.Span("Bache vial",      className="badge badge-info"),
                ], style={"display": "flex", "gap": "8px",
                          "flexWrap": "wrap", "marginBottom": "8px"}),
                html.Div(f"ID: {rpt_id} · Confianza IA: 89% · Hoy",
                         className="text-small"),
            ]),
            html.Div([
                html.Div("87%", className="priority-pct alta"),
                html.Div("prob. de atención", className="text-small"),
            ], style={"textAlign": "right"}),
        ], className="result-header"),

        html.Div([
            html.Strong("Análisis del sistema: "),
            "El reporte describe una afectación vial de alta peligrosidad. "
            "La zona registra densidad vehicular elevada. Se categoriza como "
            "bache vial con riesgo para vehículos y ciclistas.",
        ], className="ai-analysis-box"),

        html.Div([
            html.Div([
                html.Div("Categoría",       className="info-item-label"),
                html.Div("Infraestructura", className="info-item-value"),
            ], className="info-item"),
            html.Div([
                html.Div("Tipo de problema", className="info-item-label"),
                html.Div("Bache vial",       className="info-item-value"),
            ], className="info-item"),
            html.Div([
                html.Div("Confianza IA", className="info-item-label"),
                html.Div("89%",          className="info-item-value"),
            ], className="info-item"),
        ], className="info-grid"),

        html.Div([
            html.Span("✓", style={"fontSize": "14px", "flexShrink": "0"}),
            html.Div([
                html.Strong("Recomendación gubernamental: "),
                "Se recomienda enviar brigada de mantenimiento en las próximas 48 horas.",
            ]),
        ], className="alert alert-success"),

        html.Div([
            html.Div("Documento técnico generado",
                     style={"fontSize": "13px", "fontWeight": "500",
                            "color": "var(--primary)", "marginBottom": "4px"}),
            html.Div(f"PDF disponible · {rpt_id}_reporte_tecnico.pdf",
                     className="text-small", style={"marginBottom": "10px"}),
            html.Button("↓ Descargar documento técnico",
                        className="btn btn-sm btn-outline",
                        style={"color": "var(--primary)",
                               "borderColor": "var(--primary)"}),
        ], style={
            "background": "var(--primary-light)",
            "border": "1px solid rgba(15,98,254,0.2)",
            "borderRadius": "var(--radius-sm)",
            "padding": "16px",
            "marginBottom": "16px",
        }),
    ]
