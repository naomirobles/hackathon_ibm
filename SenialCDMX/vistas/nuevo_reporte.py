"""Vista: formulario de nuevo reporte ciudadano (4 pasos) con Google Maps."""
from dash import html, dcc

GMAPS_KEY = "API_KEY_AQUI"

# Coordenadas default: Col. del Valle, CDMX
DEFAULT_LAT = 19.3720
DEFAULT_LON = -99.1726


def _mapa_google(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON,
                 height: int = 220, zoom: int = 15) -> html.Div:
    """
    Mapa embebido de Google Maps vía iframe.

    Cuando tengas tu API Key real, cambia GMAPS_KEY arriba y el iframe
    mostrará el mapa interactivo completo con pin arrastrable.
    """
    if GMAPS_KEY and GMAPS_KEY != "API_KEY_AQUI":
        src = (
            f"https://www.google.com/maps/embed/v1/place"
            f"?key={GMAPS_KEY}"
            f"&q={lat},{lon}"
            f"&zoom={zoom}"
            f"&maptype=roadmap"
        )
        mapa = html.Iframe(src=src, style={"height": f"{height}px"})
    else:
        # Fallback sin key: enlace estático de OpenStreetMap
        src = (
            f"https://www.openstreetmap.org/export/embed.html"
            f"?bbox={lon-0.01}%2C{lat-0.008}%2C{lon+0.01}%2C{lat+0.008}"
            f"&layer=mapnik"
            f"&marker={lat}%2C{lon}"
        )
        mapa = html.Iframe(src=src, style={"height": f"{height}px"})

    return html.Div([
        mapa,
        html.Div(f" {lat}, {lon}", className="mapa-google-overlay"),
    ], className="mapa-google-wrap mb-16")


def _step(num: int, label: str, estado: str) -> html.Div:
    return html.Div([
        html.Div(str(num), className="step-num"),
        html.Div(label,    className="step-label"),
    ], className=f"step {estado}")


def layout_nuevo() -> html.Div:
    return html.Div(style={"maxWidth": "680px", "margin": "0 auto"}, children=[

        # Encabezado
        html.Div([
            html.Div([
                html.Div("Nuevo reporte ciudadano", className="section-title"),
                html.Div(
                    "Describe el problema y nuestro sistema lo analizará automáticamente",
                    className="section-sub",
                ),
            ])
        ], className="section-header mb-24"),

        # Indicador de pasos
        html.Div([
            _step(1, "Descripción", "active"),
            _step(2, "Ubicación",   ""),
            _step(3, "Análisis IA", ""),
            _step(4, "Resultado",   ""),
        ], className="step-indicator mb-24", id="step-indicator"),

        # PASO 1: Descripción + Capturas
        html.Div(id="form-step-1", children=[
            html.Div(className="card", children=[
                html.Div("Describe el problema", className="card-title"),
                html.Div("Puedes escribir o grabar un mensaje de voz",
                         className="card-sub"),

                html.Div([
                    html.Button("Texto",         id="tab-btn-texto",
                                className="tab-btn active", n_clicks=0),
                    html.Button("Audio → Texto", id="tab-btn-audio",
                                className="tab-btn", n_clicks=0),
                ], className="tab-bar"),

                # Pestaña texto
                html.Div(id="tab-content-texto", className="tab-content active",
                         children=[
                    html.Div([
                        html.Label("Descripción del problema", className="form-label"),
                        dcc.Textarea(
                            id="descripcion-texto",
                            className="form-textarea",
                            placeholder=(
                                "Ej: Hay un bache muy profundo en la esquina de "
                                "Insurgentes y Viaducto, lleva semanas sin atención…"
                            ),
                            style={"width": "100%", "minHeight": "100px"},
                        ),
                    ], className="form-group"),
                ]),

                # Pestaña audio
                html.Div(id="tab-content-audio", className="tab-content",
                         style={"display": "none"}, children=[
                    html.Div([
                        html.Div([
                            html.Button(
                                html.Span("🎙", style={"fontSize": "22px"}),
                                id="audio-btn", className="audio-btn", n_clicks=0,
                            ),
                            html.Div([
                                html.Div("Presiona para grabar", id="audio-status",
                                         style={"fontSize": "13px", "fontWeight": "500"}),
                                html.Div("0:00", id="audio-timer",
                                         className="text-small",
                                         style={"marginTop": "2px"}),
                            ], style={"flex": "1"}),
                        ], style={
                            "background": "var(--bg)", "borderRadius": "var(--radius-sm)",
                            "padding": "20px", "display": "flex",
                            "alignItems": "center", "gap": "16px", "marginBottom": "16px",
                        }),
                        html.Div([
                            html.Span("ℹ", style={"fontSize": "14px"}),
                            html.Div("Demo: Al detener la grabación se simulará la transcripción."),
                        ], className="alert alert-info", style={"fontSize": "12px"}),
                    ]),
                ]),

                html.Hr(className="divider"),

                # Sección de capturas múltiples 
                html.Div([
                    html.Div([
                        html.Label("Capturas fotográficas de evidencia",
                                   className="form-label"),
                        html.Span(
                            "Puedes agregar varias antes de enviar",
                            className="text-small",
                            style={"marginLeft": "8px"},
                        ),
                    ], style={"display": "flex", "alignItems": "center",
                              "marginBottom": "8px"}),

                    dcc.Upload(
                        id="upload-imagen",
                        children=html.Div([
                            html.Div("¡", className="upload-icon"),
                            html.Div([
                                html.Strong("Agregar captura"),
                                " o arrastrar imagen aquí",
                            ], className="upload-text"),
                            html.Div("JPG, PNG, WEBP · máx. 5 MB por imagen",
                                     className="text-small"),
                        ]),
                        className="upload-area",
                        accept="image/*",
                        max_size=5 * 1024 * 1024,
                        multiple=True,   # permite múltiples archivos
                    ),

                    # Galería de miniaturas
                    html.Div(id="capturas-galeria"),

                    # Contador
                    html.Div(id="capturas-contador", className="text-small",
                             style={"marginTop": "6px", "color": "var(--text3)"}),

                    # Store para guardar las capturas en sesión
                    dcc.Store(id="store-capturas", data=[]),
                ], className="form-group"),

                html.Div(
                    html.Button("Continuar → Ubicación",
                                id="btn-paso-2", className="btn btn-primary",
                                n_clicks=0),
                    style={"display": "flex", "justifyContent": "flex-end",
                           "marginTop": "20px"},
                ),
            ])
        ]),

        # PASO 2: Ubicación 
        html.Div(id="form-step-2", style={"display": "none"}, children=[
            html.Div(className="card", children=[
                html.Div("Ubicación del problema", className="card-title"),
                html.Div("Confirma la ubicación donde ocurre el problema",
                         className="card-sub"),

                _mapa_google(),

                html.Div([
                    html.Div([
                        html.Label("Latitud", className="form-label"),
                        dcc.Input(id="lat-input", value=str(DEFAULT_LAT),
                                  className="form-input",
                                  style={"width": "100%"}),
                    ], className="form-group"),
                    html.Div([
                        html.Label("Longitud", className="form-label"),
                        dcc.Input(id="lon-input", value=str(DEFAULT_LON),
                                  className="form-input",
                                  style={"width": "100%"}),
                    ], className="form-group"),
                ], className="grid-2"),

                html.Div([
                    html.Label("Dirección aproximada", className="form-label"),
                    dcc.Input(
                        value="Av. Insurgentes Sur 890, Col. del Valle, Benito Juárez, CDMX",
                        className="form-input",
                        style={"width": "100%"},
                    ),
                ], className="form-group"),

                # Nota de integración futura
                html.Div([
                    html.Span("¡", style={"fontSize": "14px"}),
                    html.Div([
                        html.Strong("Nota de integración: "),
                        "Para habilitar el mapa interactivo con pin arrastrable, "
                        "coloca tu Google Maps API Key en ",
                        html.Code("vistas/nuevo_reporte.py → GMAPS_KEY",
                                  style={"fontSize": "11px",
                                         "background": "rgba(0,0,0,0.06)",
                                         "padding": "1px 4px",
                                         "borderRadius": "3px"}),
                        ". La variable de latitud/longitud se actualizará "
                        "automáticamente al arrastrar el pin.",
                    ]),
                ], className="alert alert-info",
                   style={"fontSize": "12px", "marginBottom": "12px"}),

                html.Div([
                    html.Span("✓", style={"fontSize": "14px", "flexShrink": "0"}),
                    html.Div("Ubicación obtenida automáticamente vía GPS. "
                             "Puedes ajustar las coordenadas manualmente."),
                ], className="alert alert-success"),

                html.Div([
                    html.Button("← Volver", id="btn-paso-1-back",
                                className="btn btn-outline", n_clicks=0),
                    html.Button("Enviar y analizar →", id="btn-paso-3",
                                className="btn btn-primary", n_clicks=0),
                ], style={"display": "flex", "justifyContent": "space-between",
                          "marginTop": "8px"}),
            ])
        ]),

        # PASO 3: Procesando IA 
        html.Div(id="form-step-3", style={"display": "none"}, children=[
            html.Div(className="card", children=[
                html.Div([
                    html.Div(className="ai-spinner"),
                    html.Div("Analizando tu reporte",
                             style={"fontSize": "18px", "fontWeight": "600",
                                    "textAlign": "center"}),
                    html.Div(
                        "Nuestro sistema de IA está procesando la información "
                        "para dar una atención prioritaria",
                        className="text-muted",
                        style={"textAlign": "center", "maxWidth": "320px"},
                    ),
                    html.Ul([
                        html.Li([html.Div(className="ai-step-dot"),
                                 "Recibiendo datos del reporte"],
                                className="ai-step", id="ai-s0"),
                        html.Li([html.Div(className="ai-step-dot"),
                                 "Clasificando categoría y tipo de problema"],
                                className="ai-step", id="ai-s1"),
                        html.Li([html.Div(className="ai-step-dot"),
                                 "Consultando base de datos geográfica"],
                                className="ai-step", id="ai-s2"),
                        html.Li([html.Div(className="ai-step-dot"),
                                 "Evaluando contexto urbano y zona"],
                                className="ai-step", id="ai-s3"),
                        html.Li([html.Div(className="ai-step-dot"),
                                 "Calculando nivel de prioridad"],
                                className="ai-step", id="ai-s4"),
                        html.Li([html.Div(className="ai-step-dot"),
                                 "Analizando capturas fotográficas"],
                                className="ai-step", id="ai-s5"),
                        html.Li([html.Div(className="ai-step-dot"),
                                 "Generando documento técnico PDF"],
                                className="ai-step", id="ai-s6"),
                    ], className="ai-steps"),
                    dcc.Interval(id="ai-interval", interval=600,
                                 n_intervals=0, max_intervals=7),
                ], className="ai-processing"),
            ])
        ]),

        #  PASO 4: Resultado 
        html.Div(id="form-step-4", style={"display": "none"}, children=[
            html.Div(className="card", id="result-card"),
        ]),

        dcc.Store(id="store-ai-result"),
        dcc.Store(id="store-paso-actual", data=1),
    ])
