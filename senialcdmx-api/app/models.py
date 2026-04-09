"""
SQLAlchemy models que mapean el esquema existente en NeonDB.

Convenciones del esquema real:
  - TODOS los id son UUID con default gen_random_uuid() en PostgreSQL
  - TODOS los FK a otras tablas son UUID
  - estado es ENUM (estado_reporte), rol es ENUM (rol_usuario)
  - codigo en reportes es VARCHAR NOT NULL
  - usuario_id en reportes es NOT NULL (FK a usuarios)
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from app.database import Base

# ── Enums existentes en NeonDB (create_type=False evita que SQLAlchemy los recree) ──

estado_reporte = Enum(
    "recibido", "procesando", "procesado", "en_atencion", "resuelto", "cancelado",
    name="estado_reporte",
    create_type=False,
)

rol_usuario = Enum(
    "ciudadano", "gobierno", "admin",
    name="rol_usuario",
    create_type=False,
)

categoria_reporte = Enum(
    "riesgo", "movilidad", "otro",
    name="categoria_reporte",
    create_type=False,
)


class Usuario(Base):
    __tablename__ = "usuarios"

    id              = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    nombre_completo = Column(String, nullable=False)
    correo          = Column(String, nullable=False)
    telefono        = Column(String, nullable=True)
    direccion       = Column(Text, nullable=True)
    contrasena_hash = Column(Text, nullable=False, default="")
    rol             = Column(rol_usuario, nullable=False, default="ciudadano")


class Reporte(Base):
    __tablename__ = "reportes"

    id              = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    codigo          = Column(String, nullable=False)
    usuario_id      = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)

    descripcion       = Column(Text, nullable=False)
    descripcion_audio = Column(Text, nullable=True)
    # categoria usa el ENUM de la DB; se actualiza tras clasificación Watson x
    categoria         = Column(categoria_reporte, nullable=False, default="otro")
    estado            = Column(estado_reporte, nullable=False,
                               server_default=text("'recibido'::estado_reporte"))

    latitud           = Column(Numeric, nullable=False, default=0)
    longitud          = Column(Numeric, nullable=False, default=0)
    direccion_aprox   = Column(Text, nullable=True)
    alcaldia          = Column(String, nullable=True)
    colonia           = Column(String, nullable=True)
    # ciudad y fuente_input tienen server_default en la DB — no incluir en INSERT
    ciudad            = Column(String, nullable=False, server_default=text("'CDMX'::character varying"))
    fuente_input      = Column(String, nullable=False, server_default=text("'texto'::character varying"))
    tiene_imagen      = Column(Boolean, nullable=False, server_default=text("false"))

    created_at        = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at        = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    # Relaciones
    procesamiento   = relationship("ProcesamientoIA", back_populates="reporte", uselist=False)
    evidencias      = relationship("Evidencia", back_populates="reporte")
    documentos      = relationship("DocumentoTecnico", back_populates="reporte")
    historial       = relationship("HistorialEstado", back_populates="reporte")
    respuestas      = relationship("RespuestaGobierno", back_populates="reporte")


class ProcesamientoIA(Base):
    __tablename__ = "procesamiento_ia"

    id                     = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    reporte_id             = Column(UUID(as_uuid=True), ForeignKey("reportes.id"), nullable=False, unique=True)

    tipo_problema          = Column(Text, nullable=True)
    categoria_detectada    = Column(Text, nullable=True)
    prioridad_asignada     = Column(Text, nullable=True)
    confianza_pct          = Column(Numeric, nullable=True)
    probabilidad_atencion  = Column(Numeric, nullable=True)
    justificacion          = Column(Text, nullable=True)
    recomendacion_gobierno = Column(Text, nullable=True)
    contexto_urbano        = Column(Text, nullable=True)

    reporte = relationship("Reporte", back_populates="procesamiento")


class Evidencia(Base):
    __tablename__ = "evidencias"

    id             = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    reporte_id     = Column(UUID(as_uuid=True), ForeignKey("reportes.id"), nullable=False)
    nombre_archivo = Column(Text, nullable=True)
    url_storage    = Column(Text, nullable=True)
    created_at     = Column(DateTime(timezone=True), nullable=True)

    reporte = relationship("Reporte", back_populates="evidencias")


class DocumentoTecnico(Base):
    __tablename__ = "documentos_tecnicos"

    id             = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    reporte_id     = Column(UUID(as_uuid=True), ForeignKey("reportes.id"), nullable=False)
    nombre_archivo = Column(Text, nullable=True)
    url_storage    = Column(Text, nullable=True)
    generado_en    = Column(DateTime(timezone=True), nullable=True)
    tamanio_bytes  = Column(Integer, nullable=True)

    reporte = relationship("Reporte", back_populates="documentos")


class HistorialEstado(Base):
    __tablename__ = "historial_estado"

    id            = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    reporte_id    = Column(UUID(as_uuid=True), ForeignKey("reportes.id"), nullable=False)
    estado_previo = Column(Text, nullable=True)
    estado_nuevo  = Column(Text, nullable=True)
    cambiado_por  = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    notas         = Column(Text, nullable=True)
    created_at    = Column(DateTime(timezone=True), nullable=True)

    reporte = relationship("Reporte", back_populates="historial")


class RespuestaGobierno(Base):
    __tablename__ = "respuestas_gobierno"

    id           = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    reporte_id   = Column(UUID(as_uuid=True), ForeignKey("reportes.id"), nullable=False)
    usuario_id   = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    mensaje      = Column(Text, nullable=True)
    estado_nuevo = Column(Text, nullable=True)
    es_publica   = Column(Boolean, default=True, nullable=False)
    created_at   = Column(DateTime(timezone=True), nullable=True)

    reporte = relationship("Reporte", back_populates="respuestas")


class EntidadGobierno(Base):
    __tablename__ = "entidades_gobierno"

    id                = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    usuario_id        = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    nombre_entidad    = Column(Text, nullable=True)
    municipio         = Column(Text, nullable=True)
    alcaldia          = Column(Text, nullable=True)
    cargo_responsable = Column(Text, nullable=True)


class AsignacionGobierno(Base):
    __tablename__ = "asignaciones_gobierno"

    id               = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    reporte_id       = Column(UUID(as_uuid=True), ForeignKey("reportes.id"), nullable=False)
    asignado_a       = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    asignado_por     = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    nota_asignacion  = Column(Text, nullable=True)
    fecha_compromiso = Column(DateTime(timezone=True), nullable=True)
    created_at       = Column(DateTime(timezone=True), nullable=True)


class MetricaDiaria(Base):
    __tablename__ = "metricas_diarias"

    id                     = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    fecha                  = Column(DateTime(timezone=True), nullable=True)
    total_reportes         = Column(Integer, nullable=True)
    reportes_alta          = Column(Integer, nullable=True)
    reportes_media         = Column(Integer, nullable=True)
    reportes_baja          = Column(Integer, nullable=True)
    probabilidad_media_pct = Column(Numeric, nullable=True)
    reportes_resueltos     = Column(Integer, nullable=True)
    docs_generados         = Column(Integer, nullable=True)
    created_at             = Column(DateTime(timezone=True), nullable=True)


class CategoriaConfig(Base):
    __tablename__ = "categorias_config"

    clave       = Column(Text, primary_key=True)
    label       = Column(Text, nullable=True)
    descripcion = Column(Text, nullable=True)
    color_badge = Column(Text, nullable=True)
    activo      = Column(Boolean, default=True, nullable=False)
    orden       = Column(Integer, nullable=True)
