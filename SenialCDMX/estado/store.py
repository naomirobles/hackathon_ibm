"""
Estado global compartido de SeñalCDMX.
"""
from dash import dcc


def stores() -> list:
    """Devuelve los componentes dcc.Store para el estado global."""
    return [
        dcc.Store(id="store-usuario",           storage_type="session"),
        dcc.Store(id="store-rol",               storage_type="session"),
        dcc.Store(id="store-reportes",          storage_type="session"),
        # Flujo de nuevo reporte
        dcc.Store(id="store-report-id"),        # {report_id, codigo, status} del POST
        dcc.Store(id="store-report-resultado"), # resultado final del GET (con ia)
        dcc.Store(id="store-report-maps"),      # mapas folium {category, maps:{...}}
    ]


# Valores iniciales de demostración
DEMO_USERS = {
    "ciudadano": {
        "nombre": "Ana García",
        "email": "ciudadano@ejemplo.mx",
        "rol": "ciudadano",
    },
    "gobierno": {
        "nombre": "CDMX — Secretaría de Obras",
        "email": "gobierno@cdmx.mx",
        "rol": "gobierno",
    },
}