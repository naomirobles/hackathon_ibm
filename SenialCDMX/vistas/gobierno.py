"""Vista raíz del gobierno: dashboard con Mapa de OpenStreetMap integrado."""
from dash import html, dcc, Input, Output, State, callback
import dash_leaflet as dl  # Librería para OpenStreetMap
from componentes.navegacion import navbar
from componentes.cartas import stat_card, alert_box
from componentes.tablas import tabla_gobierno
from datos.simples import CATEGORIAS
from datos.api_client import list_reports, api_a_fila

# --- DATOS DUMMY CON COORDENADAS (CDMX) ---
# --- DATOS DUMMY AMPLIADOS (Distribución CDMX) ---
DUMMY_REPORTS = [
    # Zona Centro / Morelos
    {"id": 1, "categoria": "baches", "prioridad": "alta", "status": "pendiente", "lat": 19.4326, "lon": -99.1332},
    {"id": 2, "categoria": "luminarias", "prioridad": "media", "status": "en_proceso", "lat": 19.4270, "lon": -99.1276},
    {"id": 3, "categoria": "seguridad", "prioridad": "alta", "status": "pendiente", "lat": 19.4350, "lon": -99.1412},
    
    # Roma / Condesa
    {"id": 4, "categoria": "limpieza", "prioridad": "baja", "status": "resuelto", "lat": 19.4194, "lon": -99.1656},
    {"id": 5, "categoria": "fugas", "prioridad": "alta", "status": "pendiente", "lat": 19.4120, "lon": -99.1620},
    {"id": 6, "categoria": "baches", "prioridad": "media", "status": "en_proceso", "lat": 19.4150, "lon": -99.1700},
    
    # Polanco / Anzures
    {"id": 7, "categoria": "luminarias", "prioridad": "baja", "status": "pendiente", "lat": 19.4310, "lon": -99.1900},
    {"id": 8, "categoria": "seguridad", "prioridad": "alta", "status": "en_proceso", "lat": 19.4380, "lon": -99.2000},
    {"id": 9, "categoria": "limpieza", "prioridad": "baja", "status": "resuelto", "lat": 19.4280, "lon": -99.1850},
    
    # Coyoacán / Sur
    {"id": 10, "categoria": "fugas", "prioridad": "alta", "status": "pendiente", "lat": 19.3500, "lon": -99.1600},
    {"id": 11, "categoria": "baches", "prioridad": "media", "status": "resuelto", "lat": 19.3450, "lon": -99.1620},
    {"id": 12, "categoria": "luminarias", "prioridad": "media", "status": "en_proceso", "lat": 19.3550, "lon": -99.1500},
    
    # Santa Fe / Poniente
    {"id": 13, "categoria": "seguridad", "prioridad": "alta", "status": "pendiente", "lat": 19.3600, "lon": -99.2600},
    {"id": 14, "categoria": "baches", "prioridad": "alta", "status": "en_proceso", "lat": 19.3700, "lon": -99.2750},
    
    # Del Valle / Narvarte
    {"id": 15, "categoria": "limpieza", "prioridad": "baja", "status": "pendiente", "lat": 19.3850, "lon": -99.1550},
    {"id": 16, "categoria": "fugas", "prioridad": "media", "status": "en_proceso", "lat": 19.3950, "lon": -99.1650},
    {"id": 17, "categoria": "seguridad", "prioridad": "media", "status": "resuelto", "lat": 19.4000, "lon": -99.1500},
    
    # Azcapotzalco / Norte
    {"id": 18, "categoria": "luminarias", "prioridad": "alta", "status": "pendiente", "lat": 19.4850, "lon": -99.1850},
    {"id": 19, "categoria": "baches", "prioridad": "baja", "status": "pendiente", "lat": 19.4950, "lon": -99.1750},
    {"id": 20, "categoria": "limpieza", "prioridad": "media", "status": "resuelto", "lat": 19.4750, "lon": -99.1950},
]

def _dashboard() -> html.Div:
    return html.Div([
        html.Div([
            html.Div([
                html.Div("Panel Gubernamental", className="section-title"),
                html.Div("CDMX · Mapa Operativo en Tiempo Real", className="section-sub"),
            ]),
            html.Span("Sincronizado con brigadas", className="badge badge-info"),
        ], className="section-header mb-20"),

        # Grid de estadísticas
        html.Div(id="gov-stats-grid", className="stat-grid", style={"marginBottom": "20px"}),

        # --- SECCIÓN DEL MAPA ---
        html.Div([
            html.Div("Distribución Geográfica de Reportes", className="card-title", style={"marginBottom": "10px"}),
            html.Div([
                dl.Map([
                    dl.TileLayer(), # Fondo de OpenStreetMap
                    dl.LayerGroup(id="map-markers-layer") # Capa dinámica de marcadores
                ], 
                id="gov-map",
                center=[19.4326, -99.1332], # Centro de CDMX
                zoom=12, 
                style={'width': '100%', 'height': '400px', 'borderRadius': '12px'})
            ], className="card", style={"padding": "10px", "marginBottom": "20px"})
        ]),

        # Tabla y Alertas
        html.Div([
            html.Div(id="gov-tabla-recientes", className="card", style={"flex": "2", "padding": "20px"}),
            html.Div(id="gov-alertas", className="card", style={"flex": "1", "padding": "20px", "marginLeft": "20px"}),
        ], style={"display": "flex"}),
        
        dcc.Interval(id="gov-interval", interval=800, max_intervals=1),
    ])

def _panel_reportes() -> html.Div:
    return html.Div([
        html.Div([
            html.Div([
                html.Div("Historial de Reportes", className="section-title"),
                html.Div(id="gov-reportes-sub", className="section-sub"),
            ]),
            html.Div([
                html.Button([html.I(className="fas fa-download", style={"marginRight": "8px"}), "Exportar CSV"], 
                            className="btn btn-outline btn-sm", style={"borderRadius": "8px"}),
            ])
        ], className="section-header mb-20"),
        html.Div(id="gov-tabla-todos", className="card", style={"padding": "15px"}),
    ])


def _panel_analisis() -> html.Div:
    return html.Div([
        html.Div([
            html.Div("Análisis de Tendencias", className="section-title"),
            html.Div("Distribución por categoría y niveles críticos", className="section-sub"),
        ], className="section-header mb-20"),
        html.Div(id="gov-analisis-contenido", className="grid-2", style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "20px"}),
    ])


# ── Callback: carga datos reales (o dummy si fallan) ──────────────────────
@callback(
    Output("gov-stats-grid",        "children"),
    Output("gov-tabla-recientes",   "children"),
    Output("gov-alertas",           "children"),
    Output("map-markers-layer",     "children"), # NUEVO: Actualiza los puntos en el mapa
    Output("gov-tabla-todos",       "children"),
    Output("gov-reportes-sub",      "children"),
    Output("gov-analisis-contenido","children"),
    Input("gov-interval",           "n_intervals"),
)
def cargar_datos_gobierno(n):
    # Lógica de obtención de datos (Real o Dummy)
    try:
        reportes_api = list_reports(limit=100) or DUMMY_REPORTS
    except:
        reportes_api = DUMMY_REPORTS

    filas = [api_a_fila(r) for r in reportes_api]
    
    # 1. Crear marcadores para el mapa
    marcadores = []
    for r in reportes_api:
        # Intentar obtener lat/lon del reporte original
        lat = r.get("lat")
        lon = r.get("lon")
        
        if lat and lon:
            # Color según prioridad
            color = "red" if r.get("prioridad") == "alta" else "orange" if r.get("prioridad") == "media" else "green"
            
            marcadores.append(
                dl.CircleMarker(
                    center=[lat, lon],
                    radius=8,
                    color="white",
                    fillColor=color,
                    fillOpacity=0.8,
                    weight=2,
                    children=[
                        dl.Tooltip(f"Categoría: {r['categoria'].capitalize()}"),
                        dl.Popup([
                            html.B(f"Reporte #{r.get('id')}"),
                            html.Br(),
                            f"Prioridad: {r['prioridad']}",
                            html.Br(),
                            f"Estado: {r['status']}"
                        ])
                    ]
                )
            )

    # 2. Cálculos de estadísticas
    total = len(filas)
    altas = sum(1 for r in filas if r["prioridad"] == "alta")
    medias = sum(1 for r in filas if r["prioridad"] == "media")
    resueltos = sum(1 for r in reportes_api if r.get("status") == "resuelto")

    stats = [
        stat_card("Total Reportes", str(total), "En plataforma"),
        stat_card("Prioridad Alta", str(altas), "Requieren atención"),
        stat_card("En Proceso", str(medias), "Con brigada asignada"),
        stat_card("Resueltos", str(resueltos), "Finalizados"),
    ]

    # 3. Preparar tablas y alertas (Igual que el anterior pero con tus nombres de variables)
    tabla_rec = [
        html.Div([
            html.Div("Últimas Incidencias", className="card-title"),
            html.Span("En Vivo", className="badge badge-alta"),
        ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": "15px"}),
        tabla_gobierno(filas[:10])
    ]

    alertas = [
        html.Div("Alertas Operativas", className="card-title", style={"marginBottom": "15px"}),
        alert_box(f"Atención: {altas} casos urgentes detectados.", "warn") if altas > 0 else None,
        alert_box(f"Sistema operando con {total} reportes activos.", "info"),
    ]

    # Lógica de análisis (simplificada para el ejemplo)
    analisis_contenido = [html.Div("Análisis por categoría"), html.Div("Análisis por prioridad")]

    return stats, tabla_rec, alertas, marcadores, tabla_gobierno(filas), f"{total} reportes", analisis_contenido

# Layout principal
def layout_gobierno(usuario: str = "Gobierno CDMX") -> html.Div:
    return html.Div([
        navbar(role="gobierno", usuario=usuario),
        html.Div(className="main", children=[
            html.Div(_dashboard(),      id="panel-gov-dashboard", className="panel"),
            html.Div(_panel_reportes(),  id="panel-gov-reportes",  className="panel", style={"display": "none"}),
            html.Div(_panel_analisis(),  id="panel-gov-analisis",  className="panel", style={"display": "none"}),
        ], style={"padding": "30px", "maxWidth": "1400px", "margin": "0 auto"}),
    ], style={"backgroundColor": "#f4f7f9", "minHeight": "100vh"})


# ── Callbacks navegación ────────────────────────────────────────────
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
    show, hide = {"display": "block"}, {"display": "none"}
    active, normal = "nav-tab active", "nav-tab"

    if t == "tab-reportes":
        return hide, show, hide, normal, active, normal
    if t == "tab-analisis":
        return hide, hide, show, normal, normal, active
    return show, hide, hide, active, normal, normal