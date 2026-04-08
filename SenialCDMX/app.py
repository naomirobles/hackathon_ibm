"""
SeñalCDMX — Sistema de Reportes Urbanos
Punto de entrada principal de la aplicación Dash.

Ejecutar:
    pip install dash
    python app.py

Luego abre: http://127.0.0.1:8050
"""

import dash
from dash import Dash, html, dcc, Input, Output, callback

from estado.store import stores, DEMO_USERS
from vistas.login import layout_login
from vistas.ciudadano import layout_ciudadano
from vistas.gobierno import layout_gobierno

# ── Inicialización ───────────────────────────────────────────────────────────

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="SeñalCDMX",
)

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    *stores(),
    html.Div(id="page-content"),
])


# ── Router principal ─────────────────────────────────────────────────────────

@callback(
    Output("page-content", "children"),
    Input("url",            "pathname"),
    Input("store-usuario",  "data"),
    Input("store-rol",      "data"),
)
def router(pathname, usuario_data, rol):
    if rol == "ciudadano" and usuario_data:
        return layout_ciudadano(usuario=usuario_data.get("nombre", "Ciudadano"))
    if rol == "gobierno" and usuario_data:
        return layout_gobierno(usuario=usuario_data.get("nombre", "Gobierno"))
    return layout_login()


# ── Login ────────────────────────────────────────────────────────────────────

@callback(
    Output("store-usuario", "data"),
    Output("store-rol",     "data"),
    Output("login-error",   "children"),
    Input("btn-login-ciudadano", "n_clicks"),
    Input("btn-login-gobierno",  "n_clicks"),
    prevent_initial_call=True,
)
def do_login(n_ciudadano, n_gobierno):
    triggered = dash.ctx.triggered_id

    if triggered == "btn-login-ciudadano":
        return DEMO_USERS["ciudadano"], "ciudadano", ""
    if triggered == "btn-login-gobierno":
        return DEMO_USERS["gobierno"], "gobierno", ""
    return dash.no_update, dash.no_update, ""


# ── Logout (centralizado — btn-logout viene de la navbar) ────────────────────

@callback(
    Output("store-usuario", "data", allow_duplicate=True),
    Output("store-rol",     "data", allow_duplicate=True),
    Input("btn-logout", "n_clicks"),
    prevent_initial_call=True,
)
def do_logout(n):
    if n:
        return None, None
    return dash.no_update, dash.no_update


# ── Toggle login / registro ──────────────────────────────────────────────────

@callback(
    Output("login-form-wrap",    "style"),
    Output("register-form-wrap", "style"),
    Input("btn-show-register",   "n_clicks"),
    Input("btn-show-login",      "n_clicks"),
    prevent_initial_call=True,
)
def toggle_register(n_reg, n_login):
    if dash.ctx.triggered_id == "btn-show-register":
        return {"display": "none"}, {}
    return {}, {"display": "none"}


# ── Ejecución ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)