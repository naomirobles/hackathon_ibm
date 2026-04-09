"""Vista: listado de reportes del ciudadano con datos dummy."""
from dash import html, dcc, Input, Output, callback
from componentes.tablas import tabla_reportes
# from datos.api_client import list_reports, api_a_fila # Comentado si ya no se usa aquí temporalmente

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
    
    # -------------------------------------------------------------
    # DATOS DUMMY (MOCK)
    # Comentamos la lógica real del backend temporalmente:
    # reportes_api = list_reports(limit=50)
    # if not reportes_api:
    #     return html.Div([...])
    # filas = [api_a_fila(r) for r in reportes_api]
    # -------------------------------------------------------------
    
    # Definimos las filas manualmente. 
    # NOTA: Ajusta las claves (id, fecha, asunto, etc.) a lo que espera tu 'tabla_reportes'.
    # Datos dummy con 'probabilidad' (necesaria para la barra de progreso)
    filas = [
        {
            "id": "REP-001", 
            "fecha": "2026-04-09", 
            "asunto": "Bache en carril central", 
            "categoria": "infraestructura", 
            "prioridad": "alta",
            "status": "recibido",
            "tipo": "Bacheo",
            "descripcion": "Bache profundo que afecta la suspensión de los autos.",
            "probabilidad": 0.95, # <-- Valor para progress_cell
            "ubicacion": "Av. Insurgentes Sur 123"
        },
        {
            "id": "REP-002", 
            "fecha": "2026-04-08", 
            "asunto": "Luminaria fundida", 
            "categoria": "alumbrado", 
            "prioridad": "media",
            "status": "procesando",
            "tipo": "Iluminación",
            "descripcion": "Poste de luz sin servicio en calle oscura.",
            "probabilidad": 0.82,
            "ubicacion": "Calle Reforma 45"
        },
        {
            "id": "REP-003", 
            "fecha": "2026-04-05", 
            "asunto": "Fuga de agua potable", 
            "categoria": "agua", 
            "prioridad": "urgente",
            "status": "resuelto",
            "tipo": "Fuga",
            "descripcion": "Fuga de agua de gran magnitud en la banqueta.",
            "probabilidad": 0.98,
            "ubicacion": "Eje Central Lázaro Cárdenas"
        },
        {
            "id": "REP-004", 
            "fecha": "2026-04-01", 
            "asunto": "Acumulación de basura", 
            "categoria": "limpia", 
            "prioridad": "baja",
            "status": "rechazado",
            "tipo": "Recolección",
            "descripcion": "Bolsas de basura acumuladas en la esquina.",
            "probabilidad": 0.45,
            "ubicacion": "Colonia Condesa"
        },
        {
            "id": "REP-005", 
            "fecha": "2026-03-28", 
            "asunto": "Semáforo descompuesto", 
            "categoria": "vialidad", 
            "prioridad": "alta",
            "status": "resuelto",
            "tipo": "Tránsito",
            "descripcion": "Semáforo en mal estado genera riesgo de choque.",
            "probabilidad": 0.88,
            "ubicacion": "Intersección Av. Juárez y Balderas"
        },
    ]

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