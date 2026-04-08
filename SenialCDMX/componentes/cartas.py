"""Componentes de tarjetas reutilizables."""
from dash import html


def stat_card(label: str, value: str, delta: str = "") -> html.Div:
    """Tarjeta de estadística con valor grande."""
    children = [
        html.Div(label, className="stat-label"),
        html.Div(value, className="stat-value"),
    ]
    if delta:
        children.append(html.Div(delta, className="stat-delta"))
    return html.Div(children, className="stat-card")


def info_item(label: str, value: str, color: str = "") -> html.Div:
    """Celda de cuadrícula de información."""
    value_style = {"color": f"var({color})"} if color else {}
    return html.Div([
        html.Div(label, className="info-item-label"),
        html.Div(value, className="info-item-value", style=value_style),
    ], className="info-item")


def alert_box(text: str, tipo: str = "info") -> html.Div:
    """Caja de alerta coloreada. tipo: 'success' | 'info' | 'warn'."""
    icono = {
        "success": "+",
        "info":    "¡",
        "warn":    "-",
    }.get(tipo, "¡")
    return html.Div([
        html.Span(icono, style={"fontSize": "14px", "flexShrink": "0"}),
        html.Div(text),
    ], className=f"alert alert-{tipo}")


def map_mock(lat: float = 19.3720, lon: float = -99.1726,
             label: str = "CDMX · Benito Juárez", height: int = 140) -> html.Div:
    """Representación visual de mapa (mock)."""
    return html.Div([
        html.Div(className="map-pin"),
        html.Div(f"Lat {lat} · Lon {lon}", className="map-label"),
        html.Span(label, style={
            "position": "absolute", "bottom": "8px", "left": "8px",
            "fontSize": "11px", "color": "var(--text3)"
        }),
    ], className="map-mock", style={"height": f"{height}px"})