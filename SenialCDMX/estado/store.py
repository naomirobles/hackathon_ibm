"""
Estado global compartido de SeñalCDMX.
"""
from dash import dcc


def stores() -> list:
    """Devuelve los componentes dcc.Store para el estado global."""
    return [
        dcc.Store(id="store-usuario",  storage_type="session"),
        dcc.Store(id="store-rol",      storage_type="session"),
        dcc.Store(id="store-reportes", storage_type="session"),
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