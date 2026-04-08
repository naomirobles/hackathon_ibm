"""Componentes de tabla reutilizables."""
from dash import html
from extra.herramienta import prioridad_badge, prioridad_fill, es_pendiente
from datos.simples import CATEGORIAS


def badge(text: str, clase: str) -> html.Span:
    return html.Span(text, className=f"badge {clase}")


def progress_cell(probabilidad: int, prioridad: str) -> html.Td:
    if prioridad == "pendiente":
        return html.Td(
            html.Span("En cola…", className="text-small",
                      style={"color": "var(--text3)", "fontStyle": "italic"}),
        )
    return html.Td(html.Div([
        html.Div(html.Div(
            className=f"progress-fill {prioridad_fill(prioridad)}",
            style={"width": f"{probabilidad}%"}
        ), className="progress-bar", style={"minWidth": "60px", "flex": "1"}),
        html.Span(f"{probabilidad}%", className="text-small",
                  style={"whiteSpace": "nowrap"}),
    ], style={"display": "flex", "alignItems": "center", "gap": "8px"}))


def _fila_ciudadano(r: dict) -> html.Tr:
    cat_label = CATEGORIAS.get(r["categoria"], {}).get("label", r["categoria"])
    pri = r["prioridad"]
    pendiente = es_pendiente(r)

    tipo_cell = html.Td([
        html.Div(r["tipo"] if not pendiente else "Sin clasificar",
                 style={"fontWeight": "500", "fontSize": "13px",
                        "color": "var(--text3)" if pendiente else "inherit",
                        "fontStyle": "italic" if pendiente else "normal"}),
        html.Div(
            r["descripcion"][:60] + "…" if len(r["descripcion"]) > 60
            else r["descripcion"],
            className="text-small", style={"marginTop": "2px"},
        ),
    ])

    row_class = "report-row report-row-pendiente" if pendiente else "report-row"
    return html.Tr([
        html.Td(html.Span(r["id"], className="text-mono text-small",
                          style={"color": "var(--text3)"})),
        tipo_cell,
        html.Td(badge(cat_label, "badge-cat")),
        html.Td(badge(pri.capitalize(), prioridad_badge(pri))),
        progress_cell(r["probabilidad"], pri),
        html.Td(r["fecha"], className="text-small"),
    ], className=row_class)


def tabla_reportes(data: list, clickable: bool = True) -> html.Div:
    """Tabla de reportes ciudadanos con soporte de estado pendiente."""
    return html.Div(html.Table([
        html.Thead(html.Tr([
            html.Th("ID"), html.Th("Problema"), html.Th("Categoría"),
            html.Th("Prioridad"), html.Th("Prob. atención"), html.Th("Fecha"),
        ])),
        html.Tbody([_fila_ciudadano(r) for r in data]),
    ]), className="table-wrap")


def _fila_gobierno(r: dict) -> html.Tr:
    cat_label = CATEGORIAS.get(r["categoria"], {}).get("label", r["categoria"])
    pri = r["prioridad"]
    pendiente = es_pendiente(r)

    return html.Tr([
        html.Td(html.Span(r["id"], className="text-mono text-small")),
        html.Td(r["usuario"], className="text-small"),
        html.Td([
            html.Div(
                r["tipo"] if not pendiente else "Sin clasificar",
                style={"fontWeight": "500", "fontSize": "13px",
                       "color": "var(--text3)" if pendiente else "inherit",
                       "fontStyle": "italic" if pendiente else "normal"},
            ),
            html.Div(r["descripcion"][:55] + "…",
                     className="text-small", style={"marginTop": "2px"}),
        ]),
        html.Td(badge(cat_label, "badge-cat")),
        html.Td(badge(pri.capitalize(), prioridad_badge(pri))),
        progress_cell(r["probabilidad"], pri),
        html.Td(r["fecha"], className="text-small"),
    ], className="report-row report-row-pendiente" if pendiente else "report-row")


def tabla_gobierno(data: list) -> html.Div:
    """Tabla extendida para vista gubernamental."""
    return html.Div(html.Table([
        html.Thead(html.Tr([
            html.Th("ID"), html.Th("Ciudadano"), html.Th("Problema"),
            html.Th("Categoría"), html.Th("Prioridad"),
            html.Th("Prob. atención"), html.Th("Fecha"),
        ])),
        html.Tbody([_fila_gobierno(r) for r in data]),
    ]), className="table-wrap")