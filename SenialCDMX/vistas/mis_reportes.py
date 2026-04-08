"""Vista: listado de reportes del ciudadano (procesados + pendientes)."""
from dash import html
from datos.simples import REPORTES
from componentes.tablas import tabla_reportes


def layout_mis() -> html.Div:
    # Prueba de ejemplo
    mis = REPORTES[:3] + [r for r in REPORTES if r["status"] == "pendiente"]

    pendientes = [r for r in mis if r["status"] == "pendiente"]
    procesados = [r for r in mis if r["status"] != "pendiente"]

    return html.Div(className="main", children=[

        html.Div([
            html.Div([
                html.Div("Mis reportes", className="section-title"),
                html.Div("Historial y estado de tus reportes ciudadanos",
                         className="section-sub"),
            ]),
        ], className="section-header mb-20"),

        # Banner de pendientes si los hay
        *([html.Div([
            html.Span("⏳", style={"fontSize": "16px", "flexShrink": "0"}),
            html.Div([
                html.Strong(f"{len(pendientes)} reporte{'s' if len(pendientes) > 1 else ''} pendiente{'s' if len(pendientes) > 1 else ''} "),
                "en cola de análisis. Se procesarán automáticamente en breve.",
            ]),
        ], className="alert alert-info", style={"marginBottom": "16px"})]
          if pendientes else []),

        html.Div(className="card", children=[
            tabla_reportes(mis, clickable=True),
        ]),
    ])