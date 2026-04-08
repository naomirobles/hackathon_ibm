"""Vista raíz del gobierno: dashboard, reportes y análisis."""
from dash import html, dcc, Input, Output, callback
from componentes.navegacion import navbar
from componentes.cartas import stat_card, alert_box
from componentes.tablas import tabla_gobierno
from datos.simples import REPORTES, CATEGORIAS


# Sub-vistas

def _dashboard() -> html.Div:
    altas  = sum(1 for r in REPORTES if r["prioridad"] == "alta")
    medias = sum(1 for r in REPORTES if r["prioridad"] == "media")
    bajas  = sum(1 for r in REPORTES if r["prioridad"] == "baja")
    pendiente  = sum(1 for r in REPORTES if r["prioridad"] == "nula")
    total  = len(REPORTES)

    return html.Div([
        html.Div([
            html.Div([
                html.Div("Panel gubernamental", className="section-title"),
                html.Div("CDMX · Secretaría de Obras y Servicios",
                         className="section-sub"),
            ]),
            html.Span("Vista consolidada", className="badge badge-info"),
        ], className="section-header mb-20"),

        # Estadísticas
        html.Div([
            stat_card("Total reportes",       str(total),  "+12 esta semana"),
            stat_card("Prioridad alta",        str(altas),  "Atención inmediata"),
            stat_card("En proceso",            str(medias), "Asignados"),
            stat_card("Resueltos (30 días)",   "142",       "↑ 18% vs mes anterior"),
        ], className="stat-grid"),

        # Tabla de reportes recientes
        html.Div(className="card mb-20", children=[
            html.Div([
                html.Div([
                    html.Div("Reportes recientes", className="card-title"),
                    html.Div("Últimas 24 horas · ordenados por prioridad",
                             className="card-sub"),
                ]),
                html.Span("En vivo", className="badge badge-alta"),
            ], style={"display": "flex", "justifyContent": "space-between",
                      "alignItems": "flex-start", "marginBottom": "16px"}),
            tabla_gobierno(sorted(REPORTES,
                                  key=lambda r: {"alta": 0, "media": 1, "baja": 2, "pendiente": 3}
                                  [r["prioridad"]])),
        ]),

        # Alertas operativas
        html.Div(className="card", children=[
            html.Div("Alertas operativas", className="card-title",
                     style={"marginBottom": "16px"}),
            alert_box(
                f"Hay {altas} reportes de prioridad ALTA sin atender. "
                "Se recomienda despachar brigadas de emergencia.",
                "warn",
            ),
            alert_box(
                "Zona Benito Juárez presenta concentración de reportes viales. "
                "Considerar operativo de mantenimiento preventivo.",
                "info",
            ),
            alert_box(
                "142 reportes resueltos en los últimos 30 días. "
                "Rendimiento 18% superior al mes anterior.",
                "success",
            ),
        ]),
    ])


def _panel_reportes() -> html.Div:
    return html.Div([
        html.Div([
            html.Div([
                html.Div("Todos los reportes", className="section-title"),
                html.Div(f"{len(REPORTES)} reportes en el sistema",
                         className="section-sub"),
            ]),
            html.Button("Exportar CSV", className="btn btn-outline btn-sm"),
        ], className="section-header mb-20"),

        # Filtros rápidos
        html.Div([
            html.Span("Filtrar por prioridad:", className="text-muted",
                      style={"marginRight": "8px"}),
            html.Button("Todos",  className="btn btn-sm btn-primary",
                        style={"marginRight": "4px"}),
            html.Button("Alta",   className="btn btn-sm btn-outline",
                        style={"marginRight": "4px"}),
            html.Button("Media",  className="btn btn-sm btn-outline",
                        style={"marginRight": "4px"}),
            html.Button("Baja",   className="btn btn-sm btn-outline"),
        ], style={"marginBottom": "16px", "display": "flex",
                  "alignItems": "center", "flexWrap": "wrap", "gap": "4px"}),

        html.Div(className="card", children=[
            tabla_gobierno(REPORTES),
        ]),
    ])


def _panel_analisis() -> html.Div:
    # Conteo por categoría
    conteo = {}
    for r in REPORTES:
        cat = CATEGORIAS.get(r["categoria"], {}).get("label", r["categoria"])
        conteo[cat] = conteo.get(cat, 0) + 1

    barras = []
    max_val = max(conteo.values()) if conteo else 1
    for cat, cnt in sorted(conteo.items(), key=lambda x: -x[1]):
        pct = int(cnt / max_val * 100)
        barras.append(html.Div([
            html.Div(cat, style={"fontSize": "13px", "marginBottom": "4px",
                                 "color": "var(--text2)"}),
            html.Div([
                html.Div(className="progress-fill fill-baja",
                         style={"width": f"{pct}%", "height": "100%",
                                "background": "var(--primary)"}),
            ], className="progress-bar",
               style={"height": "10px", "marginBottom": "4px"}),
            html.Div(f"{cnt} reporte{'s' if cnt > 1 else ''}",
                     className="text-small"),
        ], style={"marginBottom": "16px"}))

    return html.Div([
        html.Div([
            html.Div("Análisis de reportes", className="section-title"),
            html.Div("Distribución por categoría y tendencias",
                     className="section-sub"),
        ], className="section-header mb-20"),

        html.Div(className="grid-2", children=[
            html.Div(className="card", children=[
                html.Div("Reportes por categoría", className="card-title",
                         style={"marginBottom": "20px"}),
                *barras,
            ]),

            html.Div(className="card", children=[
                html.Div("Distribución por prioridad", className="card-title",
                         style={"marginBottom": "20px"}),
                *[
                    html.Div([
                        html.Div([
                            html.Span(label, style={"fontSize": "13px",
                                                    "color": "var(--text2)"}),
                            html.Span(f"{cnt} ({int(cnt/len(REPORTES)*100)}%)",
                                      className="text-small"),
                        ], style={"display": "flex", "justifyContent": "space-between",
                                  "marginBottom": "4px"}),
                        html.Div(html.Div(
                            className=f"progress-fill {fill}",
                            style={"width": f"{int(cnt/len(REPORTES)*100)}%",
                                   "height": "100%"},
                        ), className="progress-bar",
                           style={"height": "10px", "marginBottom": "16px"}),
                    ])
                    for label, fill, cnt in [
                        ("Alta",  "fill-alta",  sum(1 for r in REPORTES if r["prioridad"]=="alta")),
                        ("Media", "fill-media", sum(1 for r in REPORTES if r["prioridad"]=="media")),
                        ("Baja",  "fill-baja",  sum(1 for r in REPORTES if r["prioridad"]=="baja")),
                    ]
                ],
            ]),
        ]),
    ])


# Layout principal gobierno 

def layout_gobierno(usuario: str = "CDMX — Secretaría de Obras") -> html.Div:
    return html.Div([
        navbar(role="gobierno", usuario=usuario),

        html.Div(className="main", children=[
            html.Div(_dashboard(),       id="panel-gov-dashboard", className="panel"),
            html.Div(_panel_reportes(),  id="panel-gov-reportes",  className="panel",
                     style={"display": "none"}),
            html.Div(_panel_analisis(),  id="panel-gov-analisis",  className="panel",
                     style={"display": "none"}),
        ]),
    ])


# ── Callbacks navegación gobierno ────────────────────────────────────────────

@callback(
    Output("panel-gov-dashboard", "style"),
    Output("panel-gov-reportes",  "style"),
    Output("panel-gov-analisis",  "style"),
    Output("tab-dashboard", "className"),
    Output("tab-reportes",  "className"),
    Output("tab-analisis",  "className"),
    Input("tab-dashboard", "n_clicks"),
    Input("tab-reportes",  "n_clicks"),
    Input("tab-analisis",  "n_clicks"),
    prevent_initial_call=True,
)
def switch_panel_gobierno(nd, nr, na):
    from dash import ctx
    t = ctx.triggered_id
    show, hide = {}, {"display": "none"}
    active, normal = "nav-tab active", "nav-tab"

    if t == "tab-reportes":
        return hide, show, hide, normal, active, normal
    if t == "tab-analisis":
        return hide, hide, show, normal, normal, active
    return show, hide, hide, active, normal, normal