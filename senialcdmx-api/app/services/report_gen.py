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

# ── Prompt extendido ──────────────────────────────────────────────────────────
REPORT_PROMPT = """\
Eres un analista experto en seguridad urbana y gestión de riesgos de la Ciudad de México.
Tu objetivo es generar un reporte técnico detallado basado en el reporte ciudadano y todos
los datos geoespaciales disponibles.

El reporte debe incluir obligatoriamente:
1. **Resumen ejecutivo** del problema reportado
2. **Análisis de contexto urbano** (ubicación, colonia, alcaldía, coordenadas)
3. **Hallazgos geoespaciales detallados** (cada dato cuantitativo importa)
4. **Evaluación del nivel de riesgo** con justificación técnica
5. **Prioridad de atención**: alta, media o baja — con criterios objetivos
6. **Propuestas de acción concretas** (mínimo 3, numeradas)
7. **Probabilidad de recurrencia** del evento si no se atiende

Usa un tono técnico-institucional. Máximo 400 palabras.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATOS DEL REPORTE CIUDADANO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Código de reporte : {codigo}
Tipo de problema  : {tipo_problema}
Categoría         : {categoria}
Descripción       : {descripcion}
Descripción audio : {descripcion_audio}
Fuente de entrada : {fuente_input}
Tiene imagen      : {tiene_imagen}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UBICACIÓN GEOGRÁFICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Alcaldía          : {alcaldia}
Colonia           : {colonia}
Dirección aprox.  : {direccion_aprox}
Coordenadas       : lat {latitud}, lng {longitud}
Ciudad            : {ciudad}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MÉTRICAS DEL ANÁLISIS ESPACIAL (radio 500 m)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{metricas_detalle}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HALLAZGOS GEOESPACIALES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{findings}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAPAS GEOGRÁFICAS ACTIVADAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{capas_activadas}
"""

PRIORITY_PATTERN = re.compile(
    r"\b(prioridad|priority)[:\s]+(alta|media|baja)\b",
    re.IGNORECASE,
)
PRIORITY_KEYWORDS = {
    "alta": ["alta", "urgente", "crítico", "crítica", "inmediata", "grave", "severo", "peligroso"],
    "media": ["media", "moderada", "moderado", "importante"],
    "baja": ["baja", "menor", "leve", "mínimo"],
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
        if any(kw in line.lower() for kw in ["propuesta", "acción", "accion", "recomend", "medida", "acción"]):
            capture = True
            continue
        if capture and line.startswith(("-", "•", "*", "·")):
            actions.append(line.lstrip("-•*· "))
        elif capture and re.match(r"^\d+\.", line):
            actions.append(re.sub(r"^\d+\.\s*", "", line))
        elif capture and line == "":
            if actions:
                break
    return actions[:6]  # máximo 6 propuestas


def _get_model():
    from ibm_watsonx_ai import APIClient, Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference

    credentials = Credentials(
        url=settings.watsonx_url,
        api_key=settings.watsonx_api_key,
    )
    client = APIClient(credentials=credentials, project_id=settings.watsonx_project_id)
    return ModelInference(
        model_id="meta-llama/llama-3-2-11b-vision-instruct",
        api_client=client,
        params={
            "max_new_tokens": 900,
            "temperature": 0.3,
        },
    )


def _format_findings(layers_summary: dict) -> str:
    findings = layers_summary.get("findings", [])
    if not findings:
        return "Sin hallazgos geoespaciales relevantes."
    return "\n".join(f"  • {f}" for f in findings)


def _format_capas(layers_summary: dict) -> str:
    capas = layers_summary.get("matched_layers", [])
    if not capas:
        return "Ninguna capa activada."
    return "\n".join(f"  ✓ {c}" for c in capas)


def _format_metricas_movilidad(metrics: dict) -> str:
    inter = metrics.get("intersecciones_riesgo", [])
    if isinstance(inter, list) and inter and isinstance(inter[0], dict):
        inter_txt = "; ".join(
            f"{i.get('calles','?')} [{i.get('nivel_riesgo','?').upper()}] "
            f"({i.get('n_incidentes',0)} inc.)"
            for i in inter[:5]
        )
    else:
        inter_txt = ", ".join(str(i) for i in inter[:5]) if inter else "ninguna detectada"

    return (
        f"  • Hechos de tránsito (500 m)    : {metrics.get('n_hechos_transito', 0)}\n"
        f"  • Incidentes C5 (500 m)         : {metrics.get('n_incidentes_c5', 0)}\n"
        f"  • Infracciones en alcaldía      : {metrics.get('n_infracciones_alcaldia', 0)}\n"
        f"  • Densidad de incidentes/km²    : {metrics.get('densidad_incidentes', 0.0):.2f}\n"
        f"  • Tipo de incidente frecuente   : {metrics.get('tipo_incidente_frecuente', 'sin datos')}\n"
        f"  • Intersecciones de riesgo      : {inter_txt}"
    )


def _format_metricas_riesgos(metrics: dict) -> str:
    zona = "SÍ" if metrics.get("zona_riesgo_inundacion") else "NO"
    deficit = "SÍ — cobertura insuficiente" if metrics.get("deficit_areas_verdes") else "NO"
    cob = metrics.get("cobertura_areas_verdes_m2", 0.0)
    return (
        f"  • Zona de riesgo de inundación  : {zona}\n"
        f"  • Nivel de riesgo hídrico       : {metrics.get('nivel_riesgo', 'ninguno').upper()}\n"
        f"  • Presas cercanas               : {metrics.get('n_presas_cercanas', 0)}\n"
        f"  • Puntos de captación pluvial   : {metrics.get('n_puntos_captacion', 0)}\n"
        f"  • Tiraderos clandestinos        : {metrics.get('n_tiraderos', 0)}\n"
        f"  • Cobertura de áreas verdes     : {cob:,.0f} m²\n"
        f"  • Déficit de áreas verdes       : {deficit}"
    )


def _infer_tipo_problema(category: str, descripcion: str) -> str:
    """Infiere el tipo específico de problema desde categoría + texto."""
    text = descripcion.lower()
    if category == "riesgos":
        if any(k in text for k in ["inundación", "inundacion", "encharcamiento", "agua"]):
            return "Inundación / encharcamiento"
        if any(k in text for k in ["tiradero", "basura", "residuos"]):
            return "Tiradero clandestino"
        if any(k in text for k in ["drenaje", "alcantarilla"]):
            return "Drenaje / alcantarillado"
        return "Riesgo natural"
    elif category == "movilidad":
        if any(k in text for k in ["bache", "hoyo", "hundimiento"]):
            return "Bache / deterioro del pavimento"
        if any(k in text for k in ["accidente", "choque", "atropello"]):
            return "Accidente vial"
        if any(k in text for k in ["semáforo", "semaforo", "señal", "señalamiento"]):
            return "Señalamiento vial deficiente"
        if any(k in text for k in ["cruce", "peatonal", "paso"]):
            return "Cruce peatonal inseguro"
        return "Infraestructura vial"
    return "Sin clasificar"


def _build_prompt(report, metrics: dict, layers_summary: dict, category: str) -> str:
    """Construye el prompt completo con TODA la información disponible."""
    if category == "movilidad":
        metricas_txt = _format_metricas_movilidad(metrics)
    else:
        metricas_txt = _format_metricas_riesgos(metrics)

    tipo_problema = _infer_tipo_problema(category, report.descripcion)

    return REPORT_PROMPT.format(
        codigo=getattr(report, "codigo", "N/D"),
        tipo_problema=tipo_problema,
        categoria=category,
        descripcion=report.descripcion,
        descripcion_audio=getattr(report, "descripcion_audio", None) or "No disponible",
        fuente_input=getattr(report, "fuente_input", "texto"),
        tiene_imagen="Sí" if getattr(report, "tiene_imagen", False) else "No",
        alcaldia=report.alcaldia or "No especificada",
        colonia=report.colonia or "No especificada",
        direccion_aprox=getattr(report, "direccion_aprox", None) or "No disponible",
        latitud=float(report.latitud) if report.latitud else "No disponible",
        longitud=float(report.longitud) if report.longitud else "No disponible",
        ciudad=getattr(report, "ciudad", "CDMX"),
        metricas_detalle=metricas_txt,
        findings=_format_findings(layers_summary),
        capas_activadas=_format_capas(layers_summary),
    )


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
        report       : instancia del modelo Report (con todos sus campos)
        metrics      : métricas completas del análisis espacial
        layers_summary: dict con matched_layers y findings
        category     : "riesgos" | "movilidad"
        interpretation: texto de interpretación manual (opcional, post-hackathon)

    Returns:
        ReportResult con conclusión, prioridad y acciones
    """
    # Si hay interpretación manual, enriquece los findings con ella
    if interpretation:
        enriched_summary = dict(layers_summary)
        enriched_summary["findings"] = (
            [f"[Interpretación manual] {interpretation}"]
            + layers_summary.get("findings", [])
        )
    else:
        enriched_summary = layers_summary

    prompt = _build_prompt(report, metrics, enriched_summary, category)

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
