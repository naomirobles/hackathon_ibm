"""Vista raíz del ciudadano."""
import dash
from dash import html, dcc, Input, Output, State, callback, ctx, clientside_callback
from componentes.navegacion import navbar
from extra.ibm_speech import transcribe_audio
from vistas.nuevo_reporte import layout_nuevo
from vistas.mis_reportes import layout_mis
from datos.api_client import submit_report, get_report, list_reports, api_a_fila
from componentes.tablas import tabla_reportes


def _pdf_literal(text: str) -> str:
    clean = text.encode("ascii", "ignore").decode("ascii")
    clean = clean.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"({clean})"


def _build_simple_pdf(lines: list[str]) -> bytes:
    text_lines = [line for line in lines if line]
    if not text_lines:
        text_lines = ["SeñalCDMX"]

    content_parts = ["BT", "/F1 11 Tf", "50 800 Td", "14 TL", f"{_pdf_literal(text_lines[0])} Tj"]
    for line in text_lines[1:]:
        content_parts.extend(["T*", f"{_pdf_literal(line)} Tj"])
    content_parts.append("ET")
    content_stream = "\n".join(content_parts).encode("ascii")

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        b"5 0 obj << /Length " + str(len(content_stream)).encode("ascii") + b" >> stream\n" + content_stream + b"\nendstream endobj\n",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer << /Root 1 0 R /Size {len(objects) + 1} >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def layout_ciudadano(usuario: str = "Ana García") -> html.Div:
    return html.Div([
        navbar(role="ciudadano", usuario=usuario),
        html.Div(className="main", children=[
            html.Div(layout_nuevo(), id="panel-ciudadano-nuevo"),
            html.Div(layout_mis(),   id="panel-ciudadano-mis",
                     style={"display": "none"}),
        ]),
    ])


# ── Navegación entre paneles ──────────────────────────────────────────────────

@callback(
    Output("panel-ciudadano-nuevo", "style"),
    Output("panel-ciudadano-mis",   "style"),
    Output("tab-nuevo", "className"),
    Output("tab-mis",   "className"),
    Input("tab-nuevo",    "n_clicks"),
    Input("tab-mis",      "n_clicks"),
    Input("btn-nuevo-reporte", "n_clicks", allow_optional=True),
    Input("btn-ver-mis", "n_clicks", allow_optional=True),
    State("panel-ciudadano-nuevo", "style"),
    State("panel-ciudadano-mis", "style"),
    prevent_initial_call=True,
)
def switch_panel(n_nuevo, n_mis, n_ir_nuevo, n_ver_mis, style_nuevo, style_mis):
    show, hide = {}, {"display": "none"}
    active, normal = "nav-tab active", "nav-tab"
    if ctx.triggered_id in {"tab-mis", "btn-ver-mis"}:
        return hide, show, normal, active
    return show, hide, active, normal


# Mapa → lat/lon: el postMessage del iframe actualiza el store,
# y este callback propaga los valores a los inputs de Dash.
clientside_callback(
    """
    function(paso) {
        if (!window._dashMapListenerSet) {
            window.addEventListener('message', function(e) {
                if (!e.data || e.data.type !== 'MAP_CLICK') return;
                var lat = e.data.lat;
                var lng = e.data.lng;

                // Helper: actualiza un input controlado por React
                var setter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value').set;
                function setInput(el, val) {
                    if (!el) return;
                    setter.call(el, val);
                    el.dispatchEvent(new Event('input',  {bubbles: true}));
                    el.dispatchEvent(new Event('change', {bubbles: true}));
                }

                // 1) Lat / Lon
                setInput(document.getElementById('lat-input'), lat.toFixed(6));
                setInput(document.getElementById('lon-input'), lng.toFixed(6));

                // 2) Dirección aproximada via Nominatim (reverse geocoding)
                var dirEl = document.getElementById('dir-input');
                if (dirEl) {
                    setInput(dirEl, 'Obteniendo dirección…');
                    fetch(
                        'https://nominatim.openstreetmap.org/reverse'
                        + '?format=jsonv2'
                        + '&lat=' + lat
                        + '&lon=' + lng
                        + '&accept-language=es',
                        { headers: { 'Accept-Language': 'es' } }
                    )
                    .then(function(r) { return r.json(); })
                    .then(function(data) {
                        var a = data.address || {};
                        var parts = [
                            a.road || a.pedestrian || a.footway || '',
                            a.suburb || a.neighbourhood || a.quarter || '',
                            a.city_district || a.borough || '',
                            a.city || a.town || a.village || '',
                            a.state || ''
                        ].filter(Boolean);
                        var dir = parts.length ? parts.join(', ') : (data.display_name || '');
                        setInput(dirEl, dir);
                    })
                    .catch(function() {
                        setInput(dirEl, lat.toFixed(5) + ', ' + lng.toFixed(5));
                    });
                }
            });
            window._dashMapListenerSet = true;
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("store-mapa-coords", "data"),
    Input("store-paso-actual",  "data"),
    prevent_initial_call=False,
)

# ── Tabs texto / audio ────────────────────────────────────────────────────────

@callback(
    Output("tab-content-texto", "style"),
    Output("tab-content-audio", "style"),
    Output("tab-btn-texto",     "className"),
    Output("tab-btn-audio",     "className"),
    Input("tab-btn-texto", "n_clicks"),
    Input("tab-btn-audio", "n_clicks"),
    prevent_initial_call=True,
)
def switch_input_tab(n_texto, n_audio):
    show, hide = {}, {"display": "none"}
    active, normal = "tab-btn active", "tab-btn"
    if ctx.triggered_id == "tab-btn-audio":
        return hide, show, normal, active
    return show, hide, active, normal


# ── Transcripción IBM Speech to Text ─────────────────────────────────────────

@callback(
    Output("audio-status",          "children"),
    Output("audio-timer",           "children"),
    Output("audio-transcript-wrap", "style"),
    Output("audio-transcript",      "children"),
    Input("upload-audio", "contents"),
    Input("mic-record-store", "data"),
    State("upload-audio", "filename"),
    State("mic-record-store", "data"),
    prevent_initial_call=True,
)
def transcribir_audio_upload(upload_contents, mic_store, upload_filename, mic_store_state):
    triggered = ctx.triggered_id
    audio_contents = None
    audio_filename = None

    if triggered == "upload-audio" and upload_contents:
        audio_contents = upload_contents
        audio_filename = upload_filename
    elif triggered == "mic-record-store" and isinstance(mic_store_state, dict):
        audio_payload = mic_store_state.get("audio")
        if audio_payload:
            audio_contents = audio_payload.get("contents")
            audio_filename = audio_payload.get("filename")
        elif mic_store_state.get("recording"):
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    if not audio_contents:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    try:
        transcript = transcribe_audio(audio_contents, audio_filename)
    except Exception as exc:
        return (
            f"No se pudo transcribir el audio: {exc}",
            "",
            {"display": "none"},
            "",
        )

    if not transcript:
        transcript = "IBM Speech to Text no devolvió texto reconocible para este audio."

    label = audio_filename or ("micrófono" if triggered == "mic-record-store" else "audio cargado")
    return (
        f"Transcripción completada desde {label}",
        "IBM STT · es-LA_Telephony",
        {},
        transcript,
    )


# ── Navegación del formulario de pasos ────────────────────────────────────────

@callback(
    Output("form-step-1", "style"),
    Output("form-step-2", "style"),
    Output("form-step-3", "style"),
    Output("form-step-4", "style"),
    Output("store-paso-actual", "data"),
    Input("tab-nuevo",              "n_clicks"),
    Input("btn-nuevo-reporte",      "n_clicks", allow_optional=True),
    Input("btn-paso-2",             "n_clicks"),
    Input("btn-paso-1-back",        "n_clicks"),
    Input("btn-paso-3",             "n_clicks"),
    Input("store-report-resultado", "data"),
    State("store-paso-actual",      "data"),
    prevent_initial_call=True,
)
def navegar_pasos(n_tab_nuevo, n_btn_nuevo, n2, n1back, n3, resultado, paso):
    show, hide = {}, {"display": "none"}
    t = ctx.triggered_id
    if t in {"tab-nuevo", "btn-nuevo-reporte"}:
        paso = 1
    if   t == "btn-paso-2"             and paso == 1: paso = 2
    elif t == "btn-paso-1-back"        and paso == 2: paso = 1
    elif t == "btn-paso-3"             and paso == 2: paso = 3
    elif t == "store-report-resultado" and resultado  and paso == 3: paso = 4
    return (
        show if paso == 1 else hide,
        show if paso == 2 else hide,
        show if paso == 3 else hide,
        show if paso == 4 else hide,
        paso,
    )


# ── Enviar reporte al backend ─────────────────────────────────────────────────

@callback(
    Output("store-report-id", "data"),
    Input("btn-paso-3", "n_clicks"),
    State("descripcion-texto", "value"),
    State("audio-transcript",  "children"),
    State("lat-input",         "value"),
    State("lon-input",         "value"),
    State("dir-input",         "value"),
    prevent_initial_call=True,
)
def enviar_reporte_api(n_clicks, desc_texto, desc_audio, lat, lon, direccion):
    if not n_clicks:
        return dash.no_update
    descripcion = (str(desc_audio or "").strip() or str(desc_texto or "").strip())
    if not descripcion:
        return {"error": "Sin descripción"}
    try:
        result = submit_report({
            "descripcion":   descripcion,
            "latitud":       float(lat)  if lat  else None,
            "longitud":      float(lon)  if lon  else None,
            "direccion_aprox": direccion or None,
        })
        return result   # {report_id, codigo, status}
    except Exception as e:
        return {"error": str(e)}


# ── Habilitar/deshabilitar poll-interval según el paso ───────────────────────

@callback(
    Output("poll-interval", "disabled"),
    Input("store-paso-actual", "data"),
)
def toggle_poll(paso):
    return paso != 3


# ── Polling: consultar GET /reports/{id} cada 5 s ───────────────────────────

@callback(
    Output("store-report-resultado", "data"),
    Input("poll-interval",    "n_intervals"),
    State("store-report-id",  "data"),
    State("store-paso-actual","data"),
    prevent_initial_call=True,
)
def poll_reporte(n_intervals, report_id_data, paso):
    if paso != 3 or not report_id_data:
        return dash.no_update
    if report_id_data.get("error"):
        return report_id_data           # propagar el error al resultado
    report_id = report_id_data.get("report_id")
    if not report_id:
        return dash.no_update
    try:
        result = get_report(report_id)
        if result.get("status") in ("procesado", "cancelado"):
            return result
    except Exception:
        pass
    return dash.no_update


@callback(
    Output("ai-interval", "disabled"),
    Input("store-paso-actual", "data"),
)
def toggle_interval(paso):
    return paso != 3


@callback(
    Output("ai-s0", "className"), Output("ai-s1", "className"),
    Output("ai-s2", "className"), Output("ai-s3", "className"),
    Output("ai-s4", "className"), Output("ai-s5", "className"),
    Output("ai-s6", "className"),
    Input("ai-interval", "n_intervals"),
)
def update_ai_steps(n):
    n = n or 0
    return [
        "ai-step done" if i < n else ("ai-step active" if i == n else "ai-step")
        for i in range(7)
    ]


# ── Galería de capturas ───────────────────────────────────────────────────────

@callback(
    Output("capturas-galeria",  "children"),
    Output("capturas-contador", "children"),
    Output("store-capturas",    "data"),
    Input("upload-imagen",  "contents"),
    State("upload-imagen",  "filename"),
    State("store-capturas", "data"),
    prevent_initial_call=True,
)
def agregar_capturas(contents_list, filenames, capturas_actuales):
    if not contents_list:
        return [], "", capturas_actuales or []
    capturas = list(capturas_actuales or [])
    if isinstance(contents_list, str):
        contents_list, filenames = [contents_list], [filenames]
    for content, filename in zip(contents_list, filenames):
        capturas.append({"content": content, "filename": filename, "status": "pendiente"})
    thumbs = [
        html.Div([
            html.Img(src=cap["content"],
                     style={"width": "100%", "height": "100%", "objectFit": "cover"}),
            html.Span("⏳ Pendiente", className="badge badge-pendiente captura-badge"),
        ], className="captura-thumb pendiente", title=cap["filename"])
        for cap in capturas
    ]
    total = len(capturas)
    return (
        html.Div(thumbs, className="capturas-grid"),
        f"{total} captura{'s' if total != 1 else ''} adjunta{'s' if total != 1 else ''} · se procesarán al enviar",
        capturas,
    )

@callback(
    Output("step-indicator", "children"),
    Input("store-paso-actual", "data"),
)
def actualizar_step_indicator(paso):
    paso = paso or 1

    def _step(num: int, label: str):
        if num < paso:
            estado = "done"
        elif num == paso:
            estado = "active"
        else:
            estado = ""
        return html.Div([
            html.Div(
                "✓" if num < paso else str(num),
                className="step-num",
            ),
            html.Div(label, className="step-label"),
        ], className=f"step {estado}".strip())

    return [
        _step(1, "Descripción"),
        _step(2, "Ubicación"),
        _step(3, "Análisis IA"),
        _step(4, "Resultado"),
    ]


# ── Resultado de IA ───────────────────────────────────────────────────────────

_BADGE_PRIORIDAD = {"alta": "badge-alta", "media": "badge-media", "baja": "badge-baja"}
_CATEGORIAS_LABEL = {
    "infraestructura": "Infraestructura", "seguridad": "Seguridad",
    "areas_verdes": "Áreas verdes",       "servicios": "Servicios",
    "transporte": "Transporte",           "medio_ambiente": "Medio ambiente",
}


@callback(
    Output("result-card",     "children"),
    Output("store-ai-result", "data"),
    Input("store-paso-actual",       "data"),
    State("store-capturas",          "data"),
    State("store-report-resultado",  "data"),
    prevent_initial_call=True,
)
def mostrar_resultado(paso, capturas, resultado):
    if paso != 4:
        return [], None

    n_cap = len(capturas) if capturas else 0

    # ── Extraer datos de la API ───────────────────────────────────────────────
    ia         = (resultado or {}).get("ia") or {}
    error      = (resultado or {}).get("error")
    prioridad  = ia.get("prioridad_asignada") or "media"
    categoria  = ia.get("categoria_detectada") or "infraestructura"
    tipo       = (ia.get("tipo_problema") or "N/D").replace("_", " ").capitalize()
    justific   = ia.get("justificacion") or "Análisis no disponible."
    prob       = int(ia.get("probabilidad_atencion") or 0)
    recom      = ia.get("recomendacion_gobierno") or ""
    confianza  = f"{int(ia.get('confianza_pct') or 0)}%"
    codigo     = (resultado or {}).get("codigo") or "RPT-????"

    result_data = {
        "report_id":    codigo,
        "capturas":     n_cap,
        "categoria":    _CATEGORIAS_LABEL.get(categoria, categoria),
        "tipo":         tipo,
        "prioridad":    prioridad.capitalize(),
        "confianza":    confianza,
        "descripcion":  justific,
        "recomendacion": recom,
    }

    badge_pri = _BADGE_PRIORIDAD.get(prioridad, "badge-media")

    return [
        # Cabecera resultado
        html.Div([
            html.Div([
                html.Div(
                    "⚠️ Error al procesar" if error else "Análisis completado",
                    style={"fontSize": "20px", "fontWeight": "600", "marginBottom": "8px"},
                ),
                html.Div([
                    html.Span(f"Prioridad {prioridad}", className=f"badge {badge_pri}"),
                    html.Span(_CATEGORIAS_LABEL.get(categoria, categoria), className="badge badge-cat"),
                    html.Span(tipo, className="badge badge-info"),
                ], style={"display": "flex", "gap": "8px", "flexWrap": "wrap", "marginBottom": "8px"}),
                html.Div(
                    f"ID: {codigo} · Confianza IA: {confianza} · "
                    f"{n_cap} captura{'s' if n_cap != 1 else ''} adjunta{'s' if n_cap != 1 else ''}",
                    className="text-small",
                ),
            ]),
            html.Div([
                html.Div(f"{prob}%", className=f"priority-pct {prioridad}"),
                html.Div("prob. de atención", className="text-small"),
            ], style={"textAlign": "right"}),
        ], className="result-header"),

        # Análisis
        html.Div([html.Strong("Análisis del sistema: "), justific],
                 className="ai-analysis-box"),

        # Info grid
        html.Div([
            html.Div([html.Div("Categoría",   className="info-item-label"),
                      html.Div(_CATEGORIAS_LABEL.get(categoria, categoria),
                               className="info-item-value")], className="info-item"),
            html.Div([html.Div("Tipo",        className="info-item-label"),
                      html.Div(tipo,          className="info-item-value")], className="info-item"),
            html.Div([html.Div("Confianza IA",className="info-item-label"),
                      html.Div(confianza,     className="info-item-value")], className="info-item"),
        ], className="info-grid"),

        # Capturas
        *([html.Div([
            html.Div("Evidencia fotográfica procesada",
                     style={"fontSize": "12px", "fontWeight": "600", "color": "var(--text2)",
                            "marginBottom": "8px", "textTransform": "uppercase"}),
            html.Div([
                html.Div([
                    html.Img(src=cap["content"],
                             style={"width": "100%", "height": "100%", "objectFit": "cover"}),
                    html.Span("✓ OK", className="badge badge-baja captura-badge"),
                ], className="captura-thumb") for cap in capturas
            ], className="capturas-grid"),
        ], style={"marginBottom": "16px"})] if capturas else []),

        # Recomendación
        *([html.Div([
            html.Span("✓", style={"fontSize": "14px", "flexShrink": "0"}),
            html.Div([html.Strong("Recomendación: "), recom]),
        ], className="alert alert-success")] if recom else []),

        # PDF
        html.Div([
            html.Div("Documento técnico generado",
                     style={"fontSize": "13px", "fontWeight": "500",
                            "color": "var(--primary)", "marginBottom": "4px"}),
            html.Div(f"{codigo}_reporte_tecnico.pdf", className="text-small",
                     style={"marginBottom": "10px"}),
            html.Button("↓ Descargar PDF", id="btn-descargar-pdf",
                        className="btn btn-sm btn-outline",
                        style={"color": "var(--primary)", "borderColor": "var(--primary)"}),
        ], style={"background": "var(--primary-light)",
                  "border": "1px solid rgba(15,143,74,0.2)",
                  "borderRadius": "var(--radius-sm)", "padding": "16px", "marginBottom": "16px"}),

        html.Div([
            html.Button("Crear nuevo reporte", id="btn-nuevo-reporte",
                        className="btn btn-outline", n_clicks=0),
            html.Button("Ver mis reportes", id="btn-ver-mis",
                        className="btn btn-primary", n_clicks=0),
        ], style={"display": "flex", "gap": "8px", "justifyContent": "flex-end",
                  "paddingTop": "16px", "borderTop": "1px solid var(--border)"}),
    ], result_data


@callback(
    Output("download-reporte-pdf", "data"),
    Input("btn-descargar-pdf", "n_clicks"),
    State("store-ai-result", "data"),
    prevent_initial_call=True,
)
def descargar_reporte_pdf(n_clicks, reporte):
    if not reporte:
        return dash.no_update

    lines = [
        "SeñalCDMX - Reporte tecnico",
        f"ID: {reporte.get('report_id', 'N/A')}",
        f"Prioridad: {reporte.get('prioridad', 'N/A')}",
        f"Categoria: {reporte.get('categoria', 'N/A')}",
        f"Tipo: {reporte.get('tipo', 'N/A')}",
        f"Confianza IA: {reporte.get('confianza', 'N/A')}",
        f"Capturas procesadas: {reporte.get('capturas', 0)}",
        "",
        "Resumen del sistema:",
        reporte.get("descripcion", ""),
        "",
        "Recomendacion:",
        reporte.get("recomendacion", ""),
    ]
    pdf_bytes = _build_simple_pdf(lines)
    filename = f"{reporte.get('report_id', 'reporte')}_reporte_tecnico.pdf"

    return dcc.send_bytes(lambda buffer: buffer.write(pdf_bytes), filename)
