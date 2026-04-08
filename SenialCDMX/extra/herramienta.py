"""Utilidades compartidas para SeñalCDMX."""

def prioridad_badge(p: str) -> str:
    """Devuelve la clase CSS de badge según prioridad."""
    return {
        "alta":      "badge-alta",
        "media":     "badge-media",
        "baja":      "badge-baja",
        "pendiente": "badge-pendiente",
    }.get(p, "badge-cat")


def prioridad_fill(p: str) -> str:
    """Devuelve la clase CSS de barra de progreso según prioridad."""
    return {
        "alta":  "fill-alta",
        "media": "fill-media",
        "baja":  "fill-baja",
    }.get(p, "fill-baja")


def iniciales(nombre: str) -> str:
    """Devuelve las iniciales de un nombre."""
    partes = nombre.strip().split()
    return "".join(p[0] for p in partes[:2]).upper()


def es_pendiente(reporte: dict) -> bool:
    return reporte.get("status") == "pendiente"