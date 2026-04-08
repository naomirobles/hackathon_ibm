"""
SQLAlchemy models que mapean el esquema existente en NeonDB.
Las tablas ya existen — create_all() solo las crea si no están presentes.

Nota de tipos:
  - usuarios.id  es UUID  → todos los FK que apuntan a él también son UUID
  - reportes.id  es INTEGER (SERIAL)
  - procesamiento_ia.reporte_id es INTEGER (FK a reportes.id)
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Integer, Numeric, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    nombre_completo  = Column(Text, nullable=True)
    correo           = Column(Text, nullable=True)
    telefono         = Column(Text, nullable=True)
    direccion        = Column(Text, nullable=True)
    contrasena_hash  = Column(Text, nullable=True)
    rol              = Column(Text, nullable=True)


class Reporte(Base):
    __tablename__ = "reportes"

    id               = Column(Integer, primary_key=True, index=True)
    codigo           = Column(Text, nullable=True)
    usuario_id       = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)

    descripcion      = Column(Text, nullable=False)
    descripcion_audio = Column(Text, nullable=True)
    categoria        = Column(Text, nullable=True)          # detectada por IA
    estado           = Column(Text, nullable=False, default="processing")

    latitud          = Column(Numeric, nullable=True)
    longitud         = Column(Numeric, nullable=True)
    direccion_aprox  = Column(Text, nullable=True)
    alcaldia         = Column(Text, nullable=True)
    colonia          = Column(Text, nullable=True)
    ciudad           = Column(Text, nullable=True, default="Ciudad de México")
    fuente_input     = Column(Text, nullable=True, default="web")
    tiene_imagen     = Column(Boolean, nullable=False, default=False)

    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relaciones
    procesamiento    = relationship("ProcesamientoIA", back_populates="reporte", uselist=False)
    evidencias       = relationship("Evidencia", back_populates="reporte")
    documentos       = relationship("DocumentoTecnico", back_populates="reporte")
    historial        = relationship("HistorialEstado", back_populates="reporte")
    respuestas       = relationship("RespuestaGobierno", back_populates="reporte")


class ProcesamientoIA(Base):
    __tablename__ = "procesamiento_ia"

    id                      = Column(Integer, primary_key=True, index=True)
    reporte_id              = Column(Integer, ForeignKey("reportes.id"), nullable=False, unique=True)

    tipo_problema           = Column(Text, nullable=True)    # ej. "inundacion", "bache"
    categoria_detectada     = Column(Text, nullable=True)    # "riesgos" | "movilidad"
    prioridad_asignada      = Column(Text, nullable=True)    # "alta" | "media" | "baja"
    confianza_pct           = Column(Numeric, nullable=True) # 0-100
    probabilidad_atencion   = Column(Numeric, nullable=True) # 0-100 — porcentaje de atención probable
    justificacion           = Column(Text, nullable=True)    # narrativa de análisis
    recomendacion_gobierno  = Column(Text, nullable=True)    # propuestas de acción
    contexto_urbano         = Column(Text, nullable=True)    # hallazgos geoespaciales (texto)

    reporte = relationship("Reporte", back_populates="procesamiento")


class Evidencia(Base):
    __tablename__ = "evidencias"

    id             = Column(Integer, primary_key=True, index=True)
    reporte_id     = Column(Integer, ForeignKey("reportes.id"), nullable=False)
    nombre_archivo = Column(Text, nullable=True)
    url_storage    = Column(Text, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow, nullable=False)

    reporte = relationship("Reporte", back_populates="evidencias")


class DocumentoTecnico(Base):
    __tablename__ = "documentos_tecnicos"

    id             = Column(Integer, primary_key=True, index=True)
    reporte_id     = Column(Integer, ForeignKey("reportes.id"), nullable=False)
    nombre_archivo = Column(Text, nullable=True)
    url_storage    = Column(Text, nullable=True)
    generado_en    = Column(DateTime, default=datetime.utcnow, nullable=True)
    tamanio_bytes  = Column(Integer, nullable=True)

    reporte = relationship("Reporte", back_populates="documentos")


class HistorialEstado(Base):
    __tablename__ = "historial_estado"

    id           = Column(Integer, primary_key=True, index=True)
    reporte_id   = Column(Integer, ForeignKey("reportes.id"), nullable=False)
    estado_previo = Column(Text, nullable=True)
    estado_nuevo  = Column(Text, nullable=True)
    cambiado_por  = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    notas        = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)

    reporte = relationship("Reporte", back_populates="historial")


class RespuestaGobierno(Base):
    __tablename__ = "respuestas_gobierno"

    id           = Column(Integer, primary_key=True, index=True)
    reporte_id   = Column(Integer, ForeignKey("reportes.id"), nullable=False)
    usuario_id   = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    mensaje      = Column(Text, nullable=True)
    estado_nuevo = Column(Text, nullable=True)
    es_publica   = Column(Boolean, default=True, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)

    reporte = relationship("Reporte", back_populates="respuestas")


class EntidadGobierno(Base):
    __tablename__ = "entidades_gobierno"

    id                 = Column(Integer, primary_key=True, index=True)
    usuario_id         = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    nombre_entidad     = Column(Text, nullable=True)
    municipio          = Column(Text, nullable=True)
    alcaldia           = Column(Text, nullable=True)
    cargo_responsable  = Column(Text, nullable=True)


class AsignacionGobierno(Base):
    __tablename__ = "asignaciones_gobierno"

    id                = Column(Integer, primary_key=True, index=True)
    reporte_id        = Column(Integer, ForeignKey("reportes.id"), nullable=False)
    asignado_a        = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    asignado_por      = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    nota_asignacion   = Column(Text, nullable=True)
    fecha_compromiso  = Column(DateTime, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow, nullable=False)


class MetricaDiaria(Base):
    __tablename__ = "metricas_diarias"

    id                    = Column(Integer, primary_key=True, index=True)
    fecha                 = Column(DateTime, nullable=True)
    total_reportes        = Column(Integer, nullable=True)
    reportes_alta         = Column(Integer, nullable=True)
    reportes_media        = Column(Integer, nullable=True)
    reportes_baja         = Column(Integer, nullable=True)
    probabilidad_media_pct = Column(Numeric, nullable=True)
    reportes_resueltos    = Column(Integer, nullable=True)
    docs_generados        = Column(Integer, nullable=True)
    created_at            = Column(DateTime, default=datetime.utcnow, nullable=False)


class CategoriaConfig(Base):
    __tablename__ = "categorias_config"

    clave       = Column(Text, primary_key=True)
    label       = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)
    color_badge = Column(Text, nullable=True)
    activo      = Column(Boolean, default=True, nullable=False)
    orden       = Column(Integer, nullable=True)
