"""
Conexión a PostgreSQL (NeonDB).
NeonDB requiere SSL — se pasa via connect_args para compatibilidad con psycopg2.
La URL puede traer parámetros como channel_binding=require que psycopg2 no soporta,
así que se limpian y el sslmode se configura explícitamente.
"""
from urllib.parse import urlunparse, urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def _build_engine():
    # Limpiar query params de la URL (sslmode, channel_binding, etc.)
    # y manejar SSL por connect_args donde psycopg2 los acepta bien
    parsed = urlparse(settings.database_url)
    clean_url = urlunparse(parsed._replace(query=""))

    return create_engine(
        clean_url,
        connect_args={"sslmode": "require"},
        pool_pre_ping=True,   # Reconectar si la conexión se cerró
        pool_size=5,
        max_overflow=10,
    )


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
