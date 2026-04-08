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
        "id": "550e8400-e29b-41d4-a716-446655440000",  # UUID de ejemplo
        "nombre": "Ana García",
        "email": "ciudadano@ejemplo.mx",
        "rol": "ciudadano",
    },
    "gobierno": {
        "id": "550e8400-e29b-41d4-a716-446655440001",  # UUID de ejemplo
        "nombre": "CDMX — Secretaría de Obras",
        "email": "gobierno@cdmx.mx",
        "rol": "gobierno",
    },
}