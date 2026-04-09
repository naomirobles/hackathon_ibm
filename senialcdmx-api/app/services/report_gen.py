"""
Generación del reporte final con IBM Watson x (modelo Granite).
Recibe el reporte ciudadano + métricas del análisis espacial
y devuelve: conclusión narrativa, prioridad y propuestas de acción.
"""
import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ── Prompt extendido ──────────────────────────────────────────────────────────
REPORT_PROMPT = """\
Eres un analista experto en seguridad urbana y gestión de riesgos de la Ciudad de México.
Tu objetivo es generar un reporte técnico detallado basado en TODA la información disponible.
Aprovecha cada dato numérico, geoespacial y contextual para maximizar la precisión del análisis.

El reporte debe incluir obligatoriamente:
1. **Resumen ejecutivo** del problema reportado
2. **Análisis de contexto urbano** (ubicación exacta, colonia, alcaldía, coordenadas, hora del reporte)
3. **Hallazgos geoespaciales detallados** — cita TODOS los valores numéricos disponibles
4. **Evaluación del nivel de riesgo** con justificación técnica cuantitativa
5. **Prioridad de atención**: alta, media o baja — con criterios objetivos y datos de respaldo
6. **Propuestas de acción concretas** (mínimo 4, numeradas, con responsable sugerido)
7. **Probabilidad de recurrencia** si no se atiende, con base en los datos espaciales
8. **Entidad de gobierno responsable** sugerida (alcaldía, SEMOVI, SACMEX, etc.)

Usa un tono técnico-institucional. Máximo 500 palabras.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATOS DEL REPORTE CIUDADANO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Código de reporte : {codigo}
Tipo de problema  : {tipo_problema}
Categoría         : {categoria}
Estado actual     : {estado}
Descripción       : {descripcion}
Descripción audio : {descripcion_audio}
Fuente de entrada : {fuente_input}
Tiene imagen      : {tiene_imagen}
Evidencias adjuntas: {n_evidencias}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTO TEMPORAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fecha de creación : {created_at}
Día de la semana  : {dia_semana}
Hora del reporte  : {hora_reporte}
Tiempo transcurrido: {tiempo_transcurrido}

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
MÉTRICAS ADICIONALES (todos los campos disponibles)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{metricas_extra}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HALLAZGOS GEOESPACIALES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{findings}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAPAS GEOGRÁFICAS ACTIVADAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{capas_activadas}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HISTORIAL DE ESTADOS DEL REPORTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{historial_estados}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANÁLISIS PREVIO DE IA (si existe)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{analisis_previo}
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

_DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


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
        if capture and line.startswith(("-", "•", "*", "·")):
            actions.append(line.lstrip("-•*· "))
        elif capture and re.match(r"^\d+\.", line):
            actions.append(re.sub(r"^\d+\.\s*", "", line))
        elif capture and line == "":
            if actions:
                break
    return actions[:6]


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
            "max_new_tokens": 1200,
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


def _format_metricas_extra(metrics: dict, category: str) -> str:
    """Incluye TODOS los campos del dict que no hayan sido ya presentados."""
    campos_conocidos_movilidad = {
        "n_hechos_transito", "n_incidentes_c5", "n_infracciones_alcaldia",
        "intersecciones_riesgo", "densidad_incidentes", "tipo_incidente_frecuente",
    }
    campos_conocidos_riesgos = {
        "zona_riesgo_inundacion", "nivel_riesgo", "n_presas_cercanas",
        "n_puntos_captacion", "n_tiraderos", "cobertura_areas_verdes_m2", "deficit_areas_verdes",
    }
    excluir = campos_conocidos_movilidad if category == "movilidad" else campos_conocidos_riesgos
    extras = {k: v for k, v in metrics.items() if k not in excluir}
    if not extras:
        return "  (sin campos adicionales)"
    lines = []
    for k, v in extras.items():
        if isinstance(v, (list, dict)):
            try:
                v_str = json.dumps(v, ensure_ascii=False)[:200]
            except Exception:
                v_str = str(v)[:200]
        elif isinstance(v, float):
            v_str = f"{v:.4f}"
        else:
            v_str = str(v)
        lines.append(f"  • {k}: {v_str}")
    return "\n".join(lines)


def _format_historial(report) -> str:
    """Formatea el historial de estados del reporte si está disponible."""
    try:
        historial = getattr(report, "historial", None)
        if not historial:
            return "  Sin historial de cambios registrado."
        entries = []
        for h in historial:
            ts = getattr(h, "created_at", None)
            ts_str = ts.strftime("%Y-%m-%d %H:%M") if ts else "?"
            prev = getattr(h, "estado_previo", "?") or "?"
            nuevo = getattr(h, "estado_nuevo", "?") or "?"
            notas = getattr(h, "notas", "") or ""
            entries.append(f"  [{ts_str}] {prev} → {nuevo}" + (f" ({notas})" if notas else ""))
        return "\n".join(entries) if entries else "  Sin historial de cambios registrado."
    except Exception:
        return "  No disponible."


def _format_analisis_previo(report) -> str:
    """Incluye el análisis previo de IA si el reporte ya fue procesado."""
    try:
        proc = getattr(report, "procesamiento", None)
        if not proc:
            return "  Primer procesamiento — sin análisis previo."
        lines = []
        if getattr(proc, "tipo_problema", None):
            lines.append(f"  • Tipo de problema previo    : {proc.tipo_problema}")
        if getattr(proc, "categoria_detectada", None):
            lines.append(f"  • Categoría detectada previa : {proc.categoria_detectada}")
        if getattr(proc, "prioridad_asignada", None):
            lines.append(f"  • Prioridad previa           : {proc.prioridad_asignada}")
        if getattr(proc, "confianza_pct", None) is not None:
            lines.append(f"  • Confianza IA (%)           : {proc.confianza_pct}")
        if getattr(proc, "probabilidad_atencion", None) is not None:
            lines.append(f"  • Prob. de atención (%)      : {proc.probabilidad_atencion}")
        if getattr(proc, "justificacion", None):
            snippet = str(proc.justificacion)[:300]
            lines.append(f"  • Justificación previa       : {snippet}...")
        if getattr(proc, "recomendacion_gobierno", None):
            lines.append(f"  • Recomendación previa       : {proc.recomendacion_gobierno[:200]}")
        return "\n".join(lines) if lines else "  Primer procesamiento — sin análisis previo."
    except Exception:
        return "  No disponible."


def _format_temporal(report) -> tuple[str, str, str, str]:
    """Devuelve (created_at_str, dia_semana, hora_reporte, tiempo_transcurrido)."""
    try:
        created = getattr(report, "created_at", None)
        if created is None:
            return "No disponible", "No disponible", "No disponible", "No disponible"
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        ahora = datetime.now(timezone.utc)
        delta = ahora - created
        horas_total = int(delta.total_seconds() // 3600)
        minutos = int((delta.total_seconds() % 3600) // 60)
        if horas_total >= 24:
            dias = horas_total // 24
            trans = f"{dias} día(s) {horas_total % 24}h"
        else:
            trans = f"{horas_total}h {minutos}min"
        dia = _DIAS_SEMANA[created.weekday()]
        return (
            created.strftime("%Y-%m-%d %H:%M:%S UTC"),
            dia.capitalize(),
            created.strftime("%H:%M"),
            trans,
        )
    except Exception:
        return "No disponible", "No disponible", "No disponible", "No disponible"


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
    created_at_str, dia_semana, hora_reporte, tiempo_trans = _format_temporal(report)
    metricas_extra_txt = _format_metricas_extra(metrics, category)
    historial_txt = _format_historial(report)
    analisis_previo_txt = _format_analisis_previo(report)

    return REPORT_PROMPT.format(
        codigo=getattr(report, "codigo", "N/D"),
        tipo_problema=tipo_problema,
        categoria=category,
        estado=getattr(report, "estado", "N/D") or "N/D",
        descripcion=report.descripcion,
        descripcion_audio=getattr(report, "descripcion_audio", None) or "No disponible",
        fuente_input=getattr(report, "fuente_input", "texto"),
        tiene_imagen="Sí" if getattr(report, "tiene_imagen", False) else "No",
        n_evidencias=len(getattr(report, "evidencias", None) or []),
        created_at=created_at_str,
        dia_semana=dia_semana,
        hora_reporte=hora_reporte,
        tiempo_transcurrido=tiempo_trans,
        alcaldia=report.alcaldia or "No especificada",
        colonia=report.colonia or "No especificada",
        direccion_aprox=getattr(report, "direccion_aprox", None) or "No disponible",
        latitud=float(report.latitud) if report.latitud else "No disponible",
        longitud=float(report.longitud) if report.longitud else "No disponible",
        ciudad=getattr(report, "ciudad", "CDMX"),
        metricas_detalle=metricas_txt,
        metricas_extra=metricas_extra_txt,
        findings=_format_findings(layers_summary),
        capas_activadas=_format_capas(layers_summary),
        historial_estados=historial_txt,
        analisis_previo=analisis_previo_txt,
    )


def _fallback_report(report, metrics: dict, layers_summary: dict, category: str) -> "ReportResult":
    """Genera un reporte básico cuando Watson x no está disponible."""
    tipo = _infer_tipo_problema(category, report.descripcion)
    findings = layers_summary.get("findings", [])
    findings_txt = "\n".join(f"- {f}" for f in findings) if findings else "Sin hallazgos espaciales."

    if category == "movilidad":
        n_inc = metrics.get("n_hechos_transito", 0) + metrics.get("n_incidentes_c5", 0)
        densidad = metrics.get("densidad_incidentes", 0.0)
        if n_inc > 15 or densidad > 10:
            priority = "alta"
        elif n_inc > 5:
            priority = "media"
        else:
            priority = "baja"
        context = (
            f"Hechos de tránsito: {metrics.get('n_hechos_transito', 0)}, "
            f"Incidentes C5: {metrics.get('n_incidentes_c5', 0)}, "
            f"Densidad: {densidad:.2f}/km²"
        )
    else:
        nivel = metrics.get("nivel_riesgo", "ninguno")
        zona = metrics.get("zona_riesgo_inundacion", False)
        if zona and nivel in ("alto", "Alto"):
            priority = "alta"
        elif zona:
            priority = "media"
        else:
            priority = "baja"
        context = (
            f"Zona inundación: {'Sí' if zona else 'No'}, "
            f"Nivel: {nivel}, "
            f"Tiraderos: {metrics.get('n_tiraderos', 0)}"
        )

    conclusion = (
        f"[Reporte automático — Watson x no disponible]\n"
        f"Problema: {tipo} en {report.alcaldia or 'alcaldía no especificada'}, "
        f"colonia {report.colonia or 'no especificada'}.\n"
        f"Descripción: {report.descripcion[:200]}\n"
        f"Métricas espaciales: {context}\n"
        f"Hallazgos:\n{findings_txt}"
    )
    actions = [
        f"Verificar in situ el problema de {tipo.lower()} reportado.",
        f"Coordinar con la alcaldía {report.alcaldia or 'correspondiente'} para atención.",
        "Actualizar el estado del reporte conforme avance la atención.",
        "Registrar evidencia fotográfica de la intervención.",
    ]
    return ReportResult(conclusion=conclusion, priority=priority, actions=actions)


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
        report        : instancia del modelo Reporte (con todos sus campos y relaciones)
        metrics       : métricas completas del análisis espacial
        layers_summary: dict con matched_layers y findings
        category      : "riesgos" | "movilidad"
        interpretation: texto de interpretación manual (opcional)

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
    logger.debug("Prompt enviado a Watson x (%d caracteres)", len(prompt))

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
