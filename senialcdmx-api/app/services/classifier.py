"""
Clasificación de reportes ciudadanos con IBM Watson x (modelo Granite).
Zero-shot: devuelve "riesgos" | "movilidad" | "otro"
"""
import logging
import re

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

from app.config import settings

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """\
Eres un clasificador de reportes ciudadanos para la Ciudad de México.
Clasifica el siguiente reporte en UNA de estas categorías:
- riesgos: inundaciones, encharcamientos, drenaje, zonas de peligro natural
- movilidad: accidentes viales, infracciones, cruces peligrosos, baches
- otro: cualquier otra cosa

Responde SOLO con la categoría en minúsculas, sin explicación.

Reporte: {description}
"""

VALID_CATEGORIES = {"riesgos", "movilidad", "otro"}


def _get_model() -> ModelInference:
    credentials = Credentials(
        url=settings.watsonx_url,
        api_key=settings.watsonx_api_key,
    )
    client = APIClient(credentials=credentials, project_id=settings.watsonx_project_id)
    return ModelInference(
        model_id="ibm/granite-3-8b-instruct",
        api_client=client,
        params={
            "max_new_tokens": 10,
            "temperature": 0,
            "stop_sequences": ["\n"],
        },
    )


async def classify(description: str) -> str:
    """
    Clasifica la descripción del reporte.
    Retorna "riesgos" | "movilidad" | "otro".
    """
    if not settings.watsonx_api_key:
        logger.warning("WATSONX_API_KEY no configurado — usando clasificación por palabras clave")
        return _classify_keywords(description)

    prompt = CLASSIFICATION_PROMPT.format(description=description)
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        model = _get_model()
        response = await loop.run_in_executor(
            None, lambda: model.generate_text(prompt=prompt)
        )
        category = response.strip().lower()
        # Extraer primera palabra válida
        for word in re.split(r"[\s,.]", category):
            if word in VALID_CATEGORIES:
                logger.info("Clasificación Watson x: %s", word)
                return word
        logger.warning("Watson x devolvió categoría inesperada: %r — fallback a palabras clave", category)
    except Exception as e:
        logger.error("Error en Watson x classify: %s", e)

    return _classify_keywords(description)


def _classify_keywords(description: str) -> str:
    """Clasificación de emergencia por palabras clave cuando Watson x no está disponible."""
    text = description.lower()
    riesgos_kw = [
        "inundación", "inundacion", "encharcamiento", "lluvia", "drenaje",
        "desbordamiento", "agua", "presa", "tiradero", "basura", "peligro",
        "zona de riesgo", "grieta", "hundimiento",
    ]
    movilidad_kw = [
        "accidente", "choque", "atropello", "bache", "semáforo", "semaforo",
        "infracción", "infraccion", "cruce", "peatonal", "tráfico", "trafico",
        "vialidad", "velocidad", "carro", "moto", "ciclista",
    ]
    riesgos_score = sum(1 for kw in riesgos_kw if kw in text)
    movilidad_score = sum(1 for kw in movilidad_kw if kw in text)

    if riesgos_score > movilidad_score:
        return "riesgos"
    if movilidad_score > riesgos_score:
        return "movilidad"
    return "otro"
