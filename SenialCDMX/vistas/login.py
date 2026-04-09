"""Vista de login de SeñalCDMX."""
from dash import html, dcc


def layout_login() -> html.Div:
    return html.Div(className="login-wrap", children=[
        html.Div(className="login-card", children=[

            # Logo + nombre
            html.Div([
                html.Img(src="/assets/logo.png", className="logo"),
                html.Span("SeñalCDMX", className="login-logo-text"),
            ], className="login-logo"),

            html.P("Sistema de Reportes Urbanos · CDMX", className="login-sub"),

            # Formulario de acceso
            html.Div(id="login-form-wrap", children=[
                html.Div([
                    html.Label("Correo electrónico", className="form-label"),
                    dcc.Input(
                        id="login-email",
                        type="email",
                        value="ciudadano@ejemplo.mx",
                        placeholder="tu@correo.mx",
                        className="form-input",
                        style={"width": "100%", "marginBottom": "16px"},
                    ),
                ], className="form-group"),

                html.Div([
                    html.Label("Contraseña", className="form-label"),
                    dcc.Input(
                        id="login-pass",
                        type="password",
                        value="12345678",
                        placeholder="••••••••",
                        className="form-input",
                        style={"width": "100%", "marginBottom": "20px"},
                    ),
                ], className="form-group"),

                html.Button(
                    "Iniciar sesión como ciudadano",
                    id="btn-login-ciudadano",
                    className="btn btn-primary w-full",
                    n_clicks=0,
                    style={"marginBottom": "10px"},
                ),
                html.Button(
                    "Iniciar sesión — Entidad gubernamental",
                    id="btn-login-gobierno",
                    className="btn btn-outline w-full",
                    n_clicks=0,
                ),

                html.Hr(className="divider"),

                html.Div(
                    html.Button(
                        "Crear cuenta nueva",
                        id="btn-show-register",
                        className="btn btn-sm btn-outline",
                        n_clicks=0,
                    ),
                    style={"textAlign": "center"},
                ),
            ]),

            # Formulario de registro (oculto por defecto)
            html.Div(id="register-form-wrap", style={"display": "none"}, children=[
                html.Div([
                    html.Div([
                        html.Label("Nombre completo", className="form-label"),
                        dcc.Input(placeholder="Ana García López",
                                  className="form-input",
                                  style={"width": "100%"}),
                    ], className="form-group"),
                    html.Div([
                        html.Label("Teléfono", className="form-label"),
                        dcc.Input(placeholder="55 1234 5678",
                                  className="form-input",
                                  style={"width": "100%"}),
                    ], className="form-group"),
                ], className="grid-2"),

                html.Div([
                    html.Label("Dirección", className="form-label"),
                    dcc.Input(placeholder="Av. Insurgentes 400, Col. Narvarte",
                              className="form-input",
                              style={"width": "100%"}),
                ], className="form-group"),

                html.Div([
                    html.Label("Correo electrónico", className="form-label"),
                    dcc.Input(type="email", placeholder="tu@correo.mx",
                              className="form-input",
                              style={"width": "100%"}),
                ], className="form-group"),

                html.Div([
                    html.Label("Contraseña", className="form-label"),
                    dcc.Input(type="password", placeholder="Mínimo 8 caracteres",
                              className="form-input",
                              style={"width": "100%"}),
                ], className="form-group"),

                html.Button(
                    "Registrarse y continuar",
                    id="btn-register",
                    className="btn btn-primary w-full",
                    n_clicks=0,
                    style={"marginBottom": "12px"},
                ),
                html.Div(
                    html.Button(
                        "Ya tengo cuenta",
                        id="btn-show-login",
                        className="btn btn-sm btn-outline",
                        n_clicks=0,
                    ),
                    style={"textAlign": "center"},
                ),
            ]),

            # Mensaje de error
            html.Div(id="login-error", style={"marginTop": "12px"}),
        ])
    ])