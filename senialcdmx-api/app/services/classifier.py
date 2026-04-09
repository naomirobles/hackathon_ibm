"""
Clasificación de reportes ciudadanos con IBM Watson x.

- Sin imagen: modelo Granite (texto) con generate_text()
- Con imagen: modelo Llama 3.2 Vision con chat() + image_url (igual que test.py)

Devuelve SIEMPRE "riesgos" | "movilidad" — nunca otro valor.
"""
import logging
import re

from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

from app.config import settings

logger = logging.getLogger(__name__)

# Prompt para clasificación solo texto (Granite)
CLASSIFICATION_PROMPT = """\
Eres un clasificador de reportes ciudadanos para la Ciudad de México.
Clasifica el siguiente reporte en UNA de estas dos categorías:
- riesgos: inundaciones, encharcamientos, drenaje tapado, zonas de peligro por agua, \
tiraderos clandestinos, áreas verdes, medio ambiente
- movilidad: accidentes viales, infracciones, cruces peatonales peligrosos, baches, \
semáforos, alumbrado, servicios públicos, infraestructura urbana

Responde SOLO con una palabra: riesgos   o   movilidad

Reporte: {description}
"""

# Prompt para clasificación con imagen (Llama Vision)
CLASSIFICATION_PROMPT_VISION = (
    "Eres un clasificador de reportes ciudadanos para la Ciudad de México. "
    "Analiza la imagen adjunta y la descripción del reporte. "
    "Clasifica en UNA de estas dos categorías: riesgos o movilidad. "
    "- riesgos: inundaciones, encharcamientos, drenaje, zonas de peligro natural, medio ambiente. "
    "- movilidad: accidentes viales, infracciones, cruces peligrosos, baches, servicios, infraestructura. "
    "Responde SOLO con una palabra: riesgos   o   movilidad "
    "Descripción: {description}"
)

VALID_CATEGORIES = {"riesgos", "movilidad"}

# Singletons separados por modelo
_model_text: ModelInference | None = None
_model_vision: ModelInference | None = None


def _get_model_text() -> ModelInference:
    """ingleton de Llama 3.2 Vision para clasificación con texto."""
    global _model_text
    if _model_text is None:
        credentials = Credentials(
            url=settings.watsonx_url,
            api_key=settings.watsonx_api_key,
        )
        _model_text = ModelInference(
            model_id="meta-llama/llama-3-2-11b-vision-instruct",
            credentials=credentials,
            project_id=settings.watsonx_project_id,
            params={
                "max_new_tokens": 20,
            },
        )
    return _model_text


def _get_model_vision() -> ModelInference:
    """Singleton de Llama 3.2 Vision para clasificación con imagen."""
    global _model_vision
    if _model_vision is None:
        credentials = Credentials(
            url=settings.watsonx_url,
            api_key=settings.watsonx_api_key,
        )
        _model_vision = ModelInference(
            model_id="meta-llama/llama-3-2-11b-vision-instruct",
            credentials=credentials,
            project_id=settings.watsonx_project_id,
            params={"max_tokens": 20},
        )
    return _model_vision


def _build_vision_messages(description: str, image_base64: str) -> list:
    """Construye los mensajes en el formato chat de test.py."""
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": CLASSIFICATION_PROMPT_VISION.format(description=description),
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    },
                },
            ],
        }
    ]


async def classify(description: str, image_base64: str | None = None) -> str:
    """
    Clasifica la descripción del reporte.
    Si se proporciona image_base64, usa Llama Vision con model.chat().
    Si no hay imagen, usa Granite con model.generate_text().
    Retorna SIEMPRE "riesgos" | "movilidad".
    """
    if not settings.watsonx_api_key:
        logger.warning("WATSONX_API_KEY no configurado — usando clasificación por palabras clave")
        return _classify_keywords(description)

    try:
        import asyncio
        loop = asyncio.get_running_loop()

        if image_base64:
            # --- Clasificación multimodal con imagen (igual que test.py) ---
            logger.info("Clasificando con imagen usando Llama Vision")
            model = _get_model_vision()
            messages = _build_vision_messages(description, image_base64)
            response = await loop.run_in_executor(
                None, lambda: model.chat(messages=messages)
            )
            raw = response["choices"][0]["message"]["content"]
        else:
            # --- Clasificación solo texto con Granite ---
            logger.info("Clasificando solo texto usando Granite")
            model = _get_model_text()
            prompt = CLASSIFICATION_PROMPT.format(description=description)
            raw = await loop.run_in_executor(
                None, lambda: model.generate_text(prompt=prompt)
            )

        category = raw.strip().lower()
        for word in re.split(r"[\s,.]", category):
            if word in VALID_CATEGORIES:
                logger.info("Clasificación Watson x: %s", word)
                return word
        logger.warning("Watson x devolvió categoría inesperada: %r — fallback a palabras clave", category)

    except Exception as e:
        logger.error("Error en Watson x classify: %s", e)

    return _classify_keywords(description)


def _classify_keywords(description: str) -> str:
    """
    Clasificación de emergencia por palabras clave cuando Watson x no está disponible.
    Siempre retorna 'riesgos' o 'movilidad' — nunca otro valor.
    """
    text = description.lower()
    riesgos_kw = [
        "inundación", "inundacion", "encharcamiento", "lluvia", "drenaje",
        "desbordamiento", "agua", "presa", "tiradero", "basura", "peligro",
        "zona de riesgo", "grieta", "hundimiento", "árbol", "arbol",
        "verde", "medio ambiente", "contaminacion",
    ]
    movilidad_kw = [
        "accidente", "choque", "atropello", "bache", "semáforo", "semaforo",
        "infracción", "infraccion", "cruce", "peatonal", "tráfico", "trafico",
        "vialidad", "velocidad", "carro", "moto", "ciclista", "alumbrado",
        "luminaria", "servicio", "obra", "calle", "avenida",
    ]
    riesgos_score   = sum(1 for kw in riesgos_kw   if kw in text)
    movilidad_score = sum(1 for kw in movilidad_kw if kw in text)

    # Empate o sin coincidencias → movilidad (más frecuente en reportes urbanos)
    return "riesgos" if riesgos_score > movilidad_score else "movilidad"
