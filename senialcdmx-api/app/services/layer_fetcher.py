"""
Carga las capas de datos abiertos CDMX al arrancar el servidor.
Se leen UNA SOLA VEZ y se mantienen en memoria para todos los reportes.

Estructura de archivos esperada en data/layers/:
  Riesgos:
    atlas_de_riesgo_inundaciones.gpkg
    niveles_de_inundacion.gpkg
    tiraderos_clandestinos.gpkg
    sistema_de_captacion_aguas_pluviales.gpkg
    areas_verdes_cdmx.gpkg
  Movilidad:
    CALLES.gpkg
    infracciones_al_reglamento_de_transito.csv   (solo dirección, sin coords)
    nuevo_acumulado_hechos_de_transito_2023_12.csv
    incidentes_viales_reportados_por_c5.csv
"""
import logging
from pathlib import Path
from typing import Optional, Union

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

logger = logging.getLogger(__name__)

DATA_DIR = Path("data/layers")

# Cache en memoria — se llena una sola vez en startup
# Valor: GeoDataFrame (con geometría) o DataFrame plano (sin coords, para filtro por atributo)
_layers: dict[str, dict[str, Union[gpd.GeoDataFrame, pd.DataFrame, None]]] = {
    "riesgos": {},
    "movilidad": {},
}
_loaded = False


def _read_csv(path: Path) -> pd.DataFrame:
    """Lee un CSV manejando encodings frecuentes en datos abiertos CDMX."""
    try:
        return pd.read_csv(path, encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1", low_memory=False)


def _csv_to_gdf(
    path: Path,
    lat_col: str = "latitud",
    lng_col: str = "longitud",
) -> Union[gpd.GeoDataFrame, pd.DataFrame, None]:
    """
    Lee un CSV y lo convierte a GeoDataFrame si tiene columnas de coordenadas.
    Si no tiene coords, devuelve un DataFrame plano para filtrado por atributo.
    """
    df = _read_csv(path)

    if lat_col in df.columns and lng_col in df.columns:
        df = df.copy()
        df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
        df[lng_col] = pd.to_numeric(df[lng_col], errors="coerce")
        df = df.dropna(subset=[lat_col, lng_col])
        geometry = [Point(lng, lat) for lat, lng in zip(df[lat_col], df[lng_col])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
        logger.info("Cargado %s: %d registros con coords", path.name, len(gdf))
        return gdf

    # Sin coords — DataFrame plano, disponible solo para filtrado por atributo
    logger.warning("%s sin columnas lat/lng — solo filtrado por atributo", path.name)
    return df


def _load_gpkg(path: Path) -> Optional[gpd.GeoDataFrame]:
    try:
        gdf = gpd.read_file(path)
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")
        logger.info("Cargado %s: %d registros", path.name, len(gdf))
        return gdf
    except Exception as e:
        logger.error("Error al cargar %s: %s", path.name, e)
        return None


def load_all_layers() -> None:
    """Carga todas las capas en memoria. Llamar una sola vez en startup."""
    global _loaded
    if _loaded:
        return

    logger.info("Cargando capas de datos abiertos CDMX desde %s ...", DATA_DIR)

    # ── Riesgos ────────────────────────────────────────────────────────────────
    riesgos_gpkg = {
        "atlas_inundaciones": "atlas_de_riesgo_inundaciones.gpkg",
        "niveles_inundacion": "niveles_de_inundacion.gpkg",
        "tiraderos_clandestinos": "tiraderos_clandestinos.gpkg",
        "captacion_pluvial": "sistema_de_captacion_aguas_pluviales.gpkg",
        "areas_verdes": "areas_verdes_cdmx.gpkg",
    }
    for key, filename in riesgos_gpkg.items():
        path = DATA_DIR / filename
        if path.exists():
            _layers["riesgos"][key] = _load_gpkg(path)
        else:
            logger.warning("Capa no encontrada: %s", path)
            _layers["riesgos"][key] = None

    # ── Movilidad ──────────────────────────────────────────────────────────────
    movilidad_gpkg = {
        "calles": "CALLES.gpkg",
    }
    for key, filename in movilidad_gpkg.items():
        path = DATA_DIR / filename
        if path.exists():
            _layers["movilidad"][key] = _load_gpkg(path)
        else:
            logger.warning("Capa no encontrada: %s", path)
            _layers["movilidad"][key] = None

    movilidad_csv = {
        "hechos_transito": ("nuevo_acumulado_hechos_de_transito_2023_12.csv", "latitud", "longitud"),
        "incidentes_c5": ("incidentes_viales_reportados_por_c5.csv", "latitud", "longitud"),
        "infracciones": ("infracciones_al_reglamento_de_transito.csv", None, None),
    }
    for key, (filename, lat_col, lng_col) in movilidad_csv.items():
        path = DATA_DIR / filename
        if path.exists():
            if lat_col:
                _layers["movilidad"][key] = _csv_to_gdf(path, lat_col, lng_col)
            else:
                # Sin coords — DataFrame plano para filtrado por alcaldia
                df = _read_csv(path)
                _layers["movilidad"][key] = df
                logger.info("Cargado %s (sin coords): %d registros", filename, len(df))
        else:
            logger.warning("Capa no encontrada: %s", path)
            _layers["movilidad"][key] = None

    _loaded = True
    logger.info("Capas cargadas correctamente.")


def get_layers(category: str) -> dict[str, Optional[gpd.GeoDataFrame]]:
    """
    Retorna el diccionario de capas para la categoría dada.
    category: "riesgos" | "movilidad"
    """
    if not _loaded:
        load_all_layers()
    return _layers.get(category, {})
