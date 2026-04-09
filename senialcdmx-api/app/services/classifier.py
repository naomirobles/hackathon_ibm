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
Tu tarea es decidir a cuál de estas DOS categorías pertenece el reporte:

- riesgos: reportes sobre MEDIO AMBIENTE y fenómenos naturales — inundaciones, \
encharcamientos, drenaje tapado, zonas de peligro por agua, tiraderos clandestinos, \
árboles caídos, áreas verdes, contaminación ambiental, socavones naturales.

- movilidad: reportes sobre PROBLEMAS EN CALLES y vialidad — accidentes viales, \
infracciones de tránsito, baches, semáforos descompuestos, cruces peatonales peligrosos, \
alumbrado público, obras en vía pública, señalamiento vial.

Regla clave: si el reporte menciona agua, árboles, basura o naturaleza → riesgos.
Si menciona calles, vehículos, semáforos o infraestructura vial → movilidad.

Responde ÚNICAMENTE con una palabra (riesgos o movilidad), sin explicaciones.

Reporte: {description}
Categoría:"""

# Prompt para clasificación con imagen (Llama Vision)
CLASSIFICATION_PROMPT_VISION = (
    "Eres un clasificador de reportes ciudadanos para la Ciudad de México. "
    "Analiza la imagen y la descripción. Clasifica en UNA categoría: riesgos o movilidad. "
    "- riesgos: medio ambiente, inundaciones, agua, árboles, tiraderos, contaminación. "
    "- movilidad: problemas en calles, baches, semáforos, accidentes, señalamiento vial. "
    "Responde SOLO con una palabra: riesgos o movilidad. "
    "Descripción: {description}"
)

VALID_CATEGORIES = {"riesgos", "movilidad"}

# Singletons separados por modelo
_model_text: ModelInference | None = None
_model_vision: ModelInference | None = None


def _get_model_text() -> ModelInference:
    """Singleton de IBM Granite para clasificación solo-texto."""
    global _model_text
    if _model_text is None:
        credentials = Credentials(
            url=settings.watsonx_url,
            api_key=settings.watsonx_api_key,
        )
        _model_text = ModelInference(
            model_id="ibm/granite-3-8b-instruct",
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

    Regla: riesgos = medio ambiente / agua / naturaleza
           movilidad = problemas en calles / vialidad / infraestructura vial
    """
    text = description.lower()

    # Palabras clave con peso: tupla (keyword, peso)
    riesgos_kw = [
        ("inundación", 3), ("inundacion", 3), ("encharcamiento", 3),
        ("desbordamiento", 3), ("drenaje tapado", 2), ("drenaje", 1),
        ("lluvia", 1), ("agua", 1), ("presa", 2),
        ("tiradero", 2), ("basura", 1), ("residuos", 1),
        ("contaminacion", 2), ("contaminación", 2), ("medio ambiente", 3),
        ("árbol caído", 3), ("arbol caido", 3), ("árbol", 1), ("arbol", 1),
        ("área verde", 2), ("area verde", 2), ("parque", 1),
        ("zona de riesgo", 3), ("riesgo natural", 3),
        ("grieta", 1), ("socavon", 2), ("socavón", 2),
    ]
    movilidad_kw = [
        ("accidente", 3), ("choque", 3), ("atropello", 3),
        ("bache", 3), ("hoyo en la calle", 3),
        ("semáforo", 2), ("semaforo", 2), ("señal de tránsito", 2),
        ("infracción", 2), ("infraccion", 2),
        ("cruce peatonal", 3), ("paso peatonal", 3), ("peatonal", 2),
        ("cruce", 2), ("intersección", 2), ("interseccion", 2),
        ("tráfico", 1), ("trafico", 1), ("vialidad", 2),
        ("velocidad", 1), ("carro", 1), ("moto", 1), ("ciclista", 1),
        ("alumbrado", 2), ("luminaria", 2),
        ("obra vial", 2), ("pavimento", 2), ("asfalto", 2),
        # Frases de peligro vial — calle/cruce peligroso → movilidad
        ("peligroso", 1), ("peligrosa", 1), ("peligro al cruzar", 3),
        ("miedo al pasar", 3), ("miedo al cruzar", 3),
        ("calle", 1), ("avenida", 1), ("boulevard", 1), ("crucero", 2),
    ]

    riesgos_score   = sum(peso for kw, peso in riesgos_kw   if kw in text)
    movilidad_score = sum(peso for kw, peso in movilidad_kw if kw in text)

    # Desempate: sin coincidencias en ninguna → movilidad
    # (un reporte de "cruce peligroso" sin más contexto es vialidad)
    if riesgos_score == 0 and movilidad_score == 0:
        return "movilidad"
    return "riesgos" if riesgos_score > movilidad_score else "movilidad"
