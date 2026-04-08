"""
Generación del reporte final con IBM Watson x (modelo Granite).
Recibe el reporte ciudadano + métricas del análisis espacial
y devuelve: conclusión narrativa, prioridad y propuestas de acción.
"""
import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

REPORT_PROMPT = """\
Eres un analista de seguridad urbana de la Ciudad de México.
Con base en el siguiente reporte ciudadano y los datos geoespaciales del entorno,
genera un análisis breve con:
1. Resumen del problema reportado
2. Hallazgos relevantes del entorno (datos geoespaciales)
3. Prioridad de atención: alta, media o baja — con justificación

Sé conciso. Máximo 200 palabras.

Reporte: {descripcion}
Categoría: {categoria}
Ubicación: {alcaldia}, {colonia}
Hallazgos geoespaciales: {findings}
"""

PRIORITY_PATTERN = re.compile(
    r"\b(prioridad|priority)[:\s]+(alta|media|baja)\b",
    re.IGNORECASE,
)
PRIORITY_KEYWORDS = {
    "alta": ["alta", "urgente", "crítico", "crítica", "inmediata", "grave"],
    "media": ["media", "moderada", "moderado"],
    "baja": ["baja", "menor", "leve"],
}


@dataclass
class ReportResult:
    conclusion: str
    priority: str       # "alta" | "media" | "baja"
    actions: list[str]


def _extract_priority(text: str) -> str:
    """Extrae la prioridad del texto generado por Watson x."""
    match = PRIORITY_PATTERN.search(text)
    if match:
        return match.group(2).lower()

    text_lower = text.lower()
    for priority, keywords in PRIORITY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return priority

    return "media"


def _extract_actions(text: str) -> list[str]:
    """Extrae propuestas de acción del texto."""
    actions: list[str] = []
    lines = text.split("\n")
    capture = False
    for line in lines:
        line = line.strip()
        if any(kw in line.lower() for kw in ["propuesta", "acción", "accion", "recomend", "medida"]):
            capture = True
            continue
        if capture and line.startswith(("-", "•", "*", "·")) :
            actions.append(line.lstrip("-•*· "))
        elif capture and re.match(r"^\d+\.", line):
            actions.append(re.sub(r"^\d+\.\s*", "", line))
        elif capture and line == "":
            # Dejar de capturar al encontrar línea vacía después de acciones
            if actions:
                break
    return actions[:5]  # máximo 5 propuestas


def _get_model():
    from ibm_watsonx_ai import APIClient, Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference

    credentials = Credentials(
        url=settings.watsonx_url,
        api_key=settings.watsonx_api_key,
    )
    client = APIClient(credentials=credentials, project_id=settings.watsonx_project_id)
    return ModelInference(
        model_id="ibm/granite-3-8b-instruct",
        api_client=client,
        params={
            "max_new_tokens": 500,
            "temperature": 0.3,
        },
    )


def _format_findings(layers_summary: dict) -> str:
    findings = layers_summary.get("findings", [])
    if not findings:
        return "Sin hallazgos geoespaciales relevantes."
    return " ".join(findings)


async def generate_report(
    report,
    metrics: dict,
    layers_summary: dict,
    category: str,
    interpretation: Optional[str] = None,
) -> ReportResult:
    """
    Llama a Watson x para generar el reporte final.

    Args:
        report: instancia del modelo Report
        metrics: métricas del análisis espacial
        layers_summary: dict con matched_layers y findings
        category: "riesgos" | "movilidad"
        interpretation: texto de interpretación manual (opcional, post-hackathon)

    Returns:
        ReportResult con conclusión, prioridad y acciones
    """
    findings_text = interpretation or _format_findings(layers_summary)

    prompt = REPORT_PROMPT.format(
        description=report.description,
        category=category,
        alcaldia=report.alcaldia,
        colonia=report.colonia,
        findings=findings_text,
    )

    if not settings.watsonx_api_key:
        logger.warning("WATSONX_API_KEY no configurado — usando reporte de fallback")
        return _fallback_report(report, metrics, layers_summary, category)

    try:
        loop = asyncio.get_event_loop()
        model = _get_model()
        response_text = await loop.run_in_executor(
            None, lambda: model.generate_text(prompt=prompt)
        )
        priority = _extract_priority(response_text)
        actions = _extract_actions(response_text)
        logger.info("Reporte generado por Watson x. Prioridad: %s", priority)
        return ReportResult(
            conclusion=response_text.strip(),
            priority=priority,
            actions=actions,
        )
    except Exception as e:
        logger.error("Error en Watson x generate_report: %s", e)
        return _fallback_report(report, metrics, layers_summary, category)


def _fallback_report(report, metrics: dict, layers_summary: dict, category: str) -> ReportResult:
    """Reporte de respaldo cuando Watson x no está disponible."""
    findings = layers_summary.get("findings", [])
    matched = layers_summary.get("matched_layers", [])

    # Determinar prioridad por reglas simples
    priority = "media"
    if category == "riesgos":
        nivel = metrics.get("nivel_riesgo", "ninguno")
        if nivel == "alto":
            priority = "alta"
        elif nivel == "bajo" and metrics.get("n_tiraderos", 0) == 0:
            priority = "baja"
    elif category == "movilidad":
        n = metrics.get("n_hechos_transito", 0) + metrics.get("n_incidentes_c5", 0)
        if n >= 10:
            priority = "alta"
        elif n <= 2:
            priority = "baja"

    findings_str = " ".join(findings) if findings else "Sin hallazgos disponibles."
    conclusion = (
        f"Reporte ciudadano en {report.alcaldia}, {report.colonia}. "
        f"Categoría: {category}. "
        f"Hallazgos: {findings_str} "
        f"Prioridad asignada: {priority}."
    )

    return ReportResult(
        conclusion=conclusion,
        priority=priority,
        actions=[],
    )
