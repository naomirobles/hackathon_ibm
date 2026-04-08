"""Vista raíz del ciudadano: navbar + contenido con navegación interna."""
from dash import html, dcc, Input, Output, callback
from componentes.navegacion import navbar
from vistas.nuevo_reporte import layout_nuevo
from vistas.mis_reportes import layout_mis


def layout_ciudadano(usuario: str = "Ana García") -> html.Div:
    return html.Div([
        navbar(role="ciudadano", usuario=usuario),

        html.Div(className="main", children=[
            # Panel: Nuevo reporte (activo por defecto)
            html.Div(layout_nuevo(), id="panel-ciudadano-nuevo",
                     className="panel active"),

            # Panel: Mis reportes
            html.Div(layout_mis(), id="panel-ciudadano-mis",
                     className="panel", style={"display": "none"}),
        ]),
    ])


# Callbacks de navegación ciudadano

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
    from dash import ctx
    triggered = ctx.triggered_id

    if triggered == "tab-mis":
        return (
            {"display": "none"}, {},
            "nav-tab", "nav-tab active",
        )
    # default: nuevo
    return (
        {}, {"display": "none"},
        "nav-tab active", "nav-tab",
    )


# Callbacks del formulario de nuevo reporte

@callback(
    Output("step-indicator", "children"),
    Input("store-paso-actual", "data"),
)
def actualizar_step_indicator(paso):
    from vistas.nuevo_reporte import _step

    def estado(num):
        if num < paso:
            return "done"
        if num == paso:
            return "active"
        return ""

    return [
        _step(1, "Descripción", estado(1)),
        _step(2, "Ubicación",   estado(2)),
        _step(3, "Análisis IA", estado(3)),
        _step(4, "Resultado",   estado(4)),
    ]


@callback(
    Output("form-step-1", "style"),
    Output("form-step-2", "style"),
    Output("form-step-3", "style"),
    Output("form-step-4", "style"),
    Output("store-paso-actual", "data"),
    Input("btn-paso-2",      "n_clicks"),
    Input("btn-paso-1-back", "n_clicks"),
    Input("btn-paso-3",      "n_clicks"),
    Input("ai-interval",     "n_intervals"),
    Input("store-paso-actual", "data"),
    prevent_initial_call=True,
)
def navegar_pasos(n2, n1back, n3, n_intervals, paso_actual):
    from dash import ctx
    triggered = ctx.triggered_id
    show  = {}
    hide  = {"display": "none"}

    if triggered == "btn-paso-2" and paso_actual == 1:
        paso = 2
    elif triggered == "btn-paso-1-back" and paso_actual == 2:
        paso = 1
    elif triggered == "btn-paso-3" and paso_actual == 2:
        paso = 3
    elif triggered == "ai-interval" and n_intervals >= 7 and paso_actual == 3:
        paso = 4
    else:
        paso = paso_actual

    return (
        show if paso == 1 else hide,
        show if paso == 2 else hide,
        show if paso == 3 else hide,
        show if paso == 4 else hide,
        paso,
    )


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
    clases = []
    for i in range(7):
        if i < n:
            clases.append("ai-step done")
        elif i == n:
            clases.append("ai-step active")
        else:
            clases.append("ai-step")
    return clases


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
                html.Div(
                    f"ID: {rpt_id} · Confianza IA: 89% · Hoy",
                    className="text-small",
                ),
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
                html.Div("Categoría",    className="info-item-label"),
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
        })]
