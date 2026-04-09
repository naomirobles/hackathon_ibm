"""Vista: listado de reportes del ciudadano con datos reales del backend."""
from dash import html, dcc, Input, Output, callback
from componentes.tablas import tabla_reportes
from datos.api_client import list_reports, api_a_fila


def layout_mis() -> html.Div:
    return html.Div(className="main", children=[

        html.Div([
            html.Div([
                html.Div("Mis reportes", className="section-title"),
                html.Div("Historial y estado de tus reportes ciudadanos",
                         className="section-sub"),
            ]),
        ], className="section-header mb-20"),

        html.Div(id="mis-reportes-contenido", children=[
            html.Div("Cargando reportes…",
                     className="text-small", style={"color": "var(--text3)", "padding": "24px 0"}),
        ]),

        # Dispara una sola vez al montar la vista
        dcc.Interval(id="mis-reportes-interval", interval=500, max_intervals=1),
    ])


@callback(
    Output("mis-reportes-contenido", "children"),
    Input("mis-reportes-interval",   "n_intervals"),
    prevent_initial_call=True,
)
def cargar_mis_reportes(n):
    reportes_api = list_reports(limit=50)

    if not reportes_api:
        return html.Div([
            html.Div("⚠", style={"fontSize": "24px", "marginBottom": "8px"}),
            html.Div("No se encontraron reportes o el servidor no está disponible.",
                     className="text-small"),
        ], style={"textAlign": "center", "padding": "32px 0", "color": "var(--text3)"})

    filas = [api_a_fila(r) for r in reportes_api]
    pendientes = [f for f in filas if f["status"] in ("procesando", "recibido")]
    procesados = [f for f in filas if f["status"] not in ("procesando", "recibido")]

    return html.Div([
        *([html.Div([
            html.Span("⏳", style={"fontSize": "16px", "flexShrink": "0"}),
            html.Div([
                html.Strong(
                    f"{len(pendientes)} reporte{'s' if len(pendientes) > 1 else ''} "
                    f"pendiente{'s' if len(pendientes) > 1 else ''} "
                ),
                "en cola de análisis. Se procesarán automáticamente en breve.",
            ]),
        ], className="alert alert-info", style={"marginBottom": "16px"})]
          if pendientes else []),

        html.Div(className="card", children=[
            tabla_reportes(filas, clickable=True),
        ]),
    ])
