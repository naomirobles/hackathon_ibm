"""Vista raíz del gobierno: dashboard, reportes y análisis."""
from dash import html, dcc, Input, Output, State, callback
from componentes.navegacion import navbar
from componentes.cartas import stat_card, alert_box
from componentes.tablas import tabla_gobierno
from datos.simples import CATEGORIAS
from datos.api_client import list_reports, api_a_fila


# Sub-vistas — shell vacío; los callbacks los rellenan con datos reales

def _dashboard() -> html.Div:
    return html.Div([
        html.Div([
            html.Div([
                html.Div("Panel gubernamental", className="section-title"),
                html.Div("CDMX · Secretaría de Obras y Servicios", className="section-sub"),
            ]),
            html.Span("Vista consolidada", className="badge badge-info"),
        ], className="section-header mb-20"),
        html.Div(id="gov-stats-grid",   className="stat-grid"),
        html.Div(id="gov-tabla-recientes", className="card mb-20"),
        html.Div(id="gov-alertas",      className="card"),
        dcc.Interval(id="gov-interval", interval=800, max_intervals=1),
    ])


def _panel_reportes() -> html.Div:
    return html.Div([
        html.Div([
            html.Div([
                html.Div("Todos los reportes", className="section-title"),
                html.Div(id="gov-reportes-sub", className="section-sub"),
            ]),
            html.Button("Exportar CSV", className="btn btn-outline btn-sm"),
        ], className="section-header mb-20"),
        html.Div(id="gov-tabla-todos", className="card"),
    ])


def _panel_analisis() -> html.Div:
    return html.Div([
        html.Div([
            html.Div("Análisis de reportes", className="section-title"),
            html.Div("Distribución por categoría y tendencias", className="section-sub"),
        ], className="section-header mb-20"),
        html.Div(id="gov-analisis-contenido", className="grid-2"),
    ])


# ── Callback: carga datos reales al montar el dashboard ──────────────────────

@callback(
    Output("gov-stats-grid",       "children"),
    Output("gov-tabla-recientes",  "children"),
    Output("gov-alertas",          "children"),
    Output("gov-tabla-todos",      "children"),
    Output("gov-reportes-sub",     "children"),
    Output("gov-analisis-contenido","children"),
    Input("gov-interval",          "n_intervals"),
    prevent_initial_call=True,
)
def cargar_datos_gobierno(n):
    reportes_api = list_reports(limit=100)
    filas = [api_a_fila(r) for r in reportes_api]

    total    = len(filas)
    altas    = sum(1 for r in filas if r["prioridad"] == "alta")
    medias   = sum(1 for r in filas if r["prioridad"] == "media")
    resueltos = sum(1 for r in reportes_api if r.get("status") == "resuelto")

    # ── Stats ─────────────────────────────────────────────────────────────────
    stats = html.Div([
        stat_card("Total reportes",     str(total),    "En el sistema"),
        stat_card("Prioridad alta",     str(altas),    "Atención inmediata"),
        stat_card("En proceso",         str(medias),   "Asignados"),
        stat_card("Resueltos",          str(resueltos), "Estado resuelto"),
    ], className="stat-grid")

    # ── Tabla recientes (ordenada por prioridad) ──────────────────────────────
    _orden = {"alta": 0, "media": 1, "baja": 2, "pendiente": 3}
    ordenados = sorted(filas, key=lambda r: _orden.get(r["prioridad"], 9))[:20]

    tabla_rec = [
        html.Div([
            html.Div([
                html.Div("Reportes recientes", className="card-title"),
                html.Div("Ordenados por prioridad", className="card-sub"),
            ]),
            html.Span("En vivo", className="badge badge-alta"),
        ], style={"display": "flex", "justifyContent": "space-between",
                  "alignItems": "flex-start", "marginBottom": "16px"}),
        tabla_gobierno(ordenados) if ordenados
            else html.Div("Sin reportes.", className="text-small"),
    ]

    # ── Alertas ───────────────────────────────────────────────────────────────
    alertas = [
        html.Div("Alertas operativas", className="card-title",
                 style={"marginBottom": "16px"}),
        *(
            [alert_box(
                f"Hay {altas} reportes de prioridad ALTA sin atender. "
                "Se recomienda despachar brigadas de emergencia.", "warn",
            )] if altas > 0 else []
        ),
        alert_box(
            f"{total} reportes recibidos en total. "
            f"{resueltos} resueltos hasta la fecha.", "info",
        ),
    ]

    # ── Tabla todos ───────────────────────────────────────────────────────────
    tabla_todos = tabla_gobierno(filas) if filas \
        else html.Div("Sin reportes registrados.", className="text-small")

    sub_txt = f"{total} reportes en el sistema"

    # ── Análisis: barras por categoría y prioridad ────────────────────────────
    conteo_cat: dict = {}
    for r in filas:
        cat = CATEGORIAS.get(r["categoria"], {}).get("label", r["categoria"])
        conteo_cat[cat] = conteo_cat.get(cat, 0) + 1

    max_cat = max(conteo_cat.values(), default=1)
    barras = [
        html.Div([
            html.Div(cat, style={"fontSize": "13px", "marginBottom": "4px",
                                 "color": "var(--text2)"}),
            html.Div(html.Div(
                className="progress-fill fill-baja",
                style={"width": f"{int(cnt/max_cat*100)}%", "height": "100%",
                       "background": "var(--primary)"},
            ), className="progress-bar", style={"height": "10px", "marginBottom": "4px"}),
            html.Div(f"{cnt} reporte{'s' if cnt > 1 else ''}", className="text-small"),
        ], style={"marginBottom": "16px"})
        for cat, cnt in sorted(conteo_cat.items(), key=lambda x: -x[1])
    ]

    dist_pri = [
        ("Alta",  "fill-alta",  altas),
        ("Media", "fill-media", medias),
        ("Baja",  "fill-baja",  sum(1 for r in filas if r["prioridad"] == "baja")),
    ]
    barras_pri = [
        html.Div([
            html.Div([
                html.Span(label, style={"fontSize": "13px", "color": "var(--text2)"}),
                html.Span(
                    f"{cnt} ({int(cnt/total*100) if total else 0}%)",
                    className="text-small",
                ),
            ], style={"display": "flex", "justifyContent": "space-between",
                      "marginBottom": "4px"}),
            html.Div(html.Div(
                className=f"progress-fill {fill}",
                style={"width": f"{int(cnt/total*100) if total else 0}%", "height": "100%"},
            ), className="progress-bar", style={"height": "10px", "marginBottom": "16px"}),
        ])
        for label, fill, cnt in dist_pri
    ]

    analisis = [
        html.Div(className="card", children=[
            html.Div("Reportes por categoría", className="card-title",
                     style={"marginBottom": "20px"}),
            *(barras or [html.Div("Sin datos.", className="text-small")]),
        ]),
        html.Div(className="card", children=[
            html.Div("Distribución por prioridad", className="card-title",
                     style={"marginBottom": "20px"}),
            *barras_pri,
        ]),
    ]

    return stats, tabla_rec, alertas, tabla_todos, sub_txt, analisis


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