"""
SeñalCDMX — Sistema de Reportes Urbanos
"""
import dash
from dash import Dash, html, dcc, Input, Output, State, callback

from estado.store import stores, DEMO_USERS
from vistas.login import layout_login
from vistas.ciudadano import layout_ciudadano
from vistas.gobierno import layout_gobierno

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


app.clientside_callback(
    """
    async function(nClicks, state) {
        state = state || {recording: false};
        if (!nClicks) {
            return [
                window.dash_clientside.no_update,
                window.dash_clientside.no_update,
                window.dash_clientside.no_update
            ];
        }

        if (!state.recording) {
            if (!navigator.mediaDevices || !window.MediaRecorder) {
                return [
                    {recording: false},
                    "Este navegador no soporta grabación de micrófono.",
                    "🎙 Grabar con micrófono"
                ];
            }

            try {
                const stream = await navigator.mediaDevices.getUserMedia({audio: true});
                let mimeType = "";
                if (MediaRecorder.isTypeSupported("audio/ogg;codecs=opus")) {
                    mimeType = "audio/ogg;codecs=opus";
                } else if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
                    mimeType = "audio/webm;codecs=opus";
                }

                const recorder = mimeType ? new MediaRecorder(stream, {mimeType}) : new MediaRecorder(stream);
                const chunks = [];
                const startedAt = Date.now();

                recorder.ondataavailable = (event) => {
                    if (event.data && event.data.size > 0) {
                        chunks.push(event.data);
                    }
                };

                const finished = new Promise((resolve, reject) => {
                    recorder.onstop = () => {
                        try {
                            const effectiveType = recorder.mimeType || mimeType || "audio/webm";
                            const extension = effectiveType.includes("ogg") ? "ogg" : "webm";
                            const blob = new Blob(chunks, {type: effectiveType});
                            const reader = new FileReader();
                            reader.onloadend = () => resolve({
                                recording: false,
                                startedAt,
                                durationMs: Date.now() - startedAt,
                                audio: {
                                    contents: reader.result,
                                    filename: `grabacion-${Date.now()}.${extension}`
                                }
                            });
                            reader.onerror = () => reject(reader.error || new Error("No se pudo leer el audio."));
                            reader.readAsDataURL(blob);
                        } catch (error) {
                            reject(error);
                        }
                    };

                    recorder.onerror = (event) => {
                        reject(event.error || new Error("Error de grabación."));
                    };
                });

                window.__signalcdmxRecorder = {recorder, stream, finished};
                recorder.start();
                return [
                    {recording: true, startedAt},
                    "⏺ Grabando... pulsa otra vez para detener.",
                    "⏹ Detener grabación"
                ];
            } catch (error) {
                return [
                    {recording: false},
                    `No se pudo acceder al micrófono: ${error.message}`,
                    "🎙 Grabar con micrófono"
                ];
            }
        }

        const active = window.__signalcdmxRecorder;
        if (!active) {
            return [
                {recording: false},
                "No hay una grabación activa.",
                "🎙 Grabar con micrófono"
            ];
        }

        try {
            active.recorder.stop();
            active.stream.getTracks().forEach((track) => track.stop());
            const result = await active.finished;
            window.__signalcdmxRecorder = null;
            const secs = Math.max(1, Math.round((result.durationMs || 0) / 1000));
            return [
                result,
                `✅ Audio capturado (${secs}s). Enviando a IBM Speech to Text...`,
                "🎙 Grabar con micrófono"
            ];
        } catch (error) {
            window.__signalcdmxRecorder = null;
            return [
                {recording: false},
                `No se pudo finalizar la grabación: ${error.message}`,
                "🎙 Grabar con micrófono"
            ];
        }
    }
    """,
    Output("mic-record-store", "data"),
    Output("mic-status", "children"),
    Output("mic-btn", "children"),
    Input("mic-btn", "n_clicks"),
    State("mic-record-store", "data"),
    prevent_initial_call=True,
)


# Router

@callback(
    Output("page-content", "children"),
    Input("store-usuario", "data"),
    Input("store-rol",     "data"),
)
def router(usuario_data, rol):
    if rol == "ciudadano" and usuario_data:
        return layout_ciudadano(usuario=usuario_data.get("nombre", "Ciudadano"))
    if rol == "gobierno" and usuario_data:
        return layout_gobierno(usuario=usuario_data.get("nombre", "Gobierno"))
    return layout_login()


#  Login 

@callback(
    Output("store-usuario", "data", allow_duplicate=True),
    Output("store-rol",     "data", allow_duplicate=True),
    Input("btn-login-ciudadano", "n_clicks"),
    Input("btn-login-gobierno",  "n_clicks"),
    prevent_initial_call=True,
)
def do_login(n_ciudadano, n_gobierno):
    triggered = dash.ctx.triggered_id
    if triggered == "btn-login-ciudadano":
        return DEMO_USERS["ciudadano"], "ciudadano"
    if triggered == "btn-login-gobierno":
        return DEMO_USERS["gobierno"], "gobierno"
    return dash.no_update, dash.no_update


#  Logout 

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


#  Toggle login / registro

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


if __name__ == "__main__":
    app.run(debug=True)
