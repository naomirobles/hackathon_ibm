from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(20), nullable=False, default="processing")

    # Datos de ubicación ingresados por el usuario
    description = Column(Text, nullable=False)
    street = Column(String(255), nullable=False)
    ext_number = Column(String(20), nullable=False)
    int_number = Column(String(20), nullable=True)
    postal_code = Column(String(10), nullable=False)
    alcaldia = Column(String(100), nullable=False)
    colonia = Column(String(100), nullable=False)
    between_street_1 = Column(String(255), nullable=True)
    between_street_2 = Column(String(255), nullable=True)

    # Coordenadas (pueden venir del usuario o de geocodificación)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)

    # Resultados del pipeline
    category = Column(String(50), nullable=True)
    priority = Column(String(10), nullable=True)
    analysis = Column(Text, nullable=True)
    layers_summary = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
