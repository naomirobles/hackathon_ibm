"""Barra de navegación de SeñalCDMX."""
from dash import html, dcc


def navbar(role: str = "ciudadano", usuario: str = "Ciudadano") -> html.Div:
    """
    Navbar principal.

    Args:
        role:    'ciudadano' | 'gobierno'
        usuario: nombre del usuario autenticado
    """
    initials = "".join(p[0] for p in usuario.strip().split()[:2]).upper()

    if role == "ciudadano":
        tabs = html.Div([
            html.Button("＋ Nuevo reporte", id="tab-nuevo",
                        className="nav-tab active",
                        n_clicks=0),
            html.Button("☰ Mis reportes",  id="tab-mis",
                        className="nav-tab",
                        n_clicks=0),
        ], className="nav-tabs")
    else:
        tabs = html.Div([
            html.Button("Dashboard",  id="tab-dashboard",
                        className="nav-tab active", n_clicks=0),
            html.Button("Reportes",   id="tab-reportes",
                        className="nav-tab", n_clicks=0),
            html.Button("Análisis",   id="tab-analisis",
                        className="nav-tab", n_clicks=0),
        ], className="nav-tabs")

    avatar_style = {} if role == "ciudadano" else {"background": "#096b36"}

    return html.Nav(className="nav", children=[
        html.Div([
            html.Img(src="/assets/logo.png", className="logo"),
            html.Span("SeñalCDMX", className="brand-text"),
        ], className="nav-brand"),

        tabs,

        html.Div([
            html.Div([
                html.Div(initials, className="avatar-sm", style=avatar_style),
                html.Span(usuario.split("—")[0].strip()),
            ], className="nav-user"),
            html.Button(
                "- Salir",
                id="btn-logout",
                className="btn-logout",
                n_clicks=0,
                title="Cerrar sesión",
            ),
        ], style={"display": "flex", "alignItems": "center", "gap": "4px"}),
    ])
