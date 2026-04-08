from datetime import datetime

from pydantic import BaseModel


# ── Request: lo que envía el frontend ─────────────────────────────────────────

class ReportCreate(BaseModel):
    descripcion: str
    descripcion_audio: str | None = None

    direccion_aprox: str | None = None
    alcaldia: str | None = None
    colonia: str | None = None
    ciudad: str = "Ciudad de México"
    latitud: float | None = None
    longitud: float | None = None

    fuente_input: str = "web"
    tiene_imagen: bool = False
    usuario_id: str | None = None   # UUID del usuario autenticado; None = anónimo


# ── Response: POST /reports ────────────────────────────────────────────────────

class ReportCreatedResponse(BaseModel):
    report_id: str      # UUID
    codigo: str
    status: str


# ── Response: GET /reports/{id} ────────────────────────────────────────────────

class ProcesamientoIAResponse(BaseModel):
    tipo_problema: str | None = None
    categoria_detectada: str | None = None
    prioridad_asignada: str | None = None
    confianza_pct: float | None = None
    probabilidad_atencion: float | None = None
    justificacion: str | None = None
    recomendacion_gobierno: str | None = None
    contexto_urbano: str | None = None

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    report_id: str      # UUID
    codigo: str | None = None
    status: str
    latitud: float | None = None
    longitud: float | None = None
    alcaldia: str | None = None
    colonia: str | None = None
    created_at: datetime | None = None

    ia: ProcesamientoIAResponse | None = None

    class Config:
        from_attributes = True


# ── Response: GET /reports (lista) ────────────────────────────────────────────

class ReportListItem(BaseModel):
    report_id: str      # UUID
    codigo: str | None = None
    status: str
    categoria: str | None = None
    alcaldia: str | None = None
    prioridad: str | None = None
    probabilidad_atencion: float | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
