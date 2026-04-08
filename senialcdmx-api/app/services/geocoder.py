"""
Geocodificación de direcciones y registros sin coordenadas.
Usa Nominatim (OpenStreetMap) — sin costo.
"""
import asyncio
import logging
from typing import Optional

import geopandas as gpd
import pandas as pd
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
from geopy.geocoders import Nominatim
from shapely.geometry import Point

from app.config import settings

logger = logging.getLogger(__name__)

_geocoder = Nominatim(user_agent=settings.nominatim_user_agent, timeout=10)


def _build_address(report) -> str:
    parts = [
        f"{report.street} {report.ext_number}",
        report.colonia,
        report.alcaldia,
        report.postal_code,
        "Ciudad de México, México",
    ]
    return ", ".join(p for p in parts if p)


async def geocode(report) -> tuple[Optional[float], Optional[float]]:
    """
    Convierte los campos de dirección del reporte en (lat, lng).
    Retorna (None, None) si la geocodificación falla.
    """
    address = _build_address(report)
    logger.info("Geocodificando: %s", address)

    loop = asyncio.get_event_loop()
    try:
        location = await loop.run_in_executor(
            None, lambda: _geocoder.geocode(address, country_codes="MX")
        )
        if location:
            logger.info("Coordenadas: %.6f, %.6f", location.latitude, location.longitude)
            return location.latitude, location.longitude

        # Fallback: solo alcaldía + CDMX
        fallback = f"{report.alcaldia}, Ciudad de México, México"
        location = await loop.run_in_executor(
            None, lambda: _geocoder.geocode(fallback, country_codes="MX")
        )
        if location:
            logger.warning("Geocodificación con fallback (alcaldía): %.6f, %.6f", location.latitude, location.longitude)
            return location.latitude, location.longitude

    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        logger.error("Error de geocodificación: %s", e)

    return None, None


async def geocode_records(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Geocodifica registros de un GeoDataFrame que carecen de geometría.
    Usa columnas 'en_la_calle', 'colonia', 'alcaldia' si existen.
    Retorna el GeoDataFrame con geometría asignada donde fue posible.
    """
    if gdf is None or gdf.empty:
        return gdf

    # Si ya tiene geometría válida, no hacer nada
    if "geometry" in gdf.columns and gdf.geometry.notna().all():
        return gdf

    logger.info("Geocodificando %d registros sin coordenadas...", len(gdf))
    points = []

    # Determinar columnas disponibles para construir dirección
    has_street = "en_la_calle" in gdf.columns
    has_colonia = "colonia" in gdf.columns
    has_alcaldia = "alcaldia" in gdf.columns

    async def _geocode_row(row) -> Optional[Point]:
        parts = []
        if has_street and pd.notna(row.get("en_la_calle")):
            parts.append(str(row["en_la_calle"]))
        if has_colonia and pd.notna(row.get("colonia")):
            parts.append(str(row["colonia"]))
        if has_alcaldia and pd.notna(row.get("alcaldia")):
            parts.append(str(row["alcaldia"]))
        parts.append("Ciudad de México, México")
        address = ", ".join(parts)

        loop = asyncio.get_event_loop()
        try:
            location = await loop.run_in_executor(
                None, lambda: _geocoder.geocode(address, country_codes="MX")
            )
            if location:
                return Point(location.longitude, location.latitude)
        except (GeocoderTimedOut, GeocoderUnavailable):
            pass
        return None

    # Geocodificar en lotes para no saturar Nominatim
    BATCH_SIZE = 10
    for i in range(0, len(gdf), BATCH_SIZE):
        batch = gdf.iloc[i : i + BATCH_SIZE]
        tasks = [_geocode_row(row) for _, row in batch.iterrows()]
        results = await asyncio.gather(*tasks)
        points.extend(results)
        await asyncio.sleep(1)  # Respetar rate limit de Nominatim

    gdf = gdf.copy()
    gdf["geometry"] = points
    gdf = gdf[gdf["geometry"].notna()]
    gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")
    logger.info("Geocodificados %d/%d registros", len(gdf), len(points))
    return gdf
