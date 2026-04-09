"""
Cliente HTTP para el backend SeñalCDMX (FastAPI en localhost:8000).
Toda la comunicación con la base de datos pasa por aquí.
"""
import os
import requests

API_URL = os.getenv("SENIAL_API_URL", "http://localhost:8000")
_TIMEOUT = 10


def submit_report(data: dict) -> dict:
    """POST /reports — envía un reporte ciudadano y devuelve {report_id, codigo, status}."""
    r = requests.post(f"{API_URL}/reports", json=data, timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


def get_report(report_id: str) -> dict:
    """GET /reports/{id} — devuelve el reporte con resultado de IA si ya procesó."""
    r = requests.get(f"{API_URL}/reports/{report_id}", timeout=_TIMEOUT)
    r.raise_for_status()
    return r.json()


def list_reports(limit: int = 50) -> list[dict]:
    """GET /reports — lista de reportes para dashboard."""
    try:
        r = requests.get(f"{API_URL}/reports", params={"limit": limit}, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return []


def api_a_fila(r: dict) -> dict:
    """Convierte un item de GET /reports al formato que esperan las tablas."""
    fecha = (r.get("created_at") or "")[:10] or "N/D"
    prioridad = r.get("prioridad") or "pendiente"
    return {
        "id":          r.get("codigo") or r.get("report_id", "")[:8],
        "tipo":        "—",
        "descripcion": r.get("alcaldia") or r.get("status") or "—",
        "categoria":   r.get("categoria") or "infraestructura",
        "prioridad":   prioridad,
        "probabilidad": int(r.get("probabilidad_atencion") or 0),
        "fecha":       fecha,
        "status":      r.get("status", "procesando"),
        "usuario":     "Ciudadano",
    }
