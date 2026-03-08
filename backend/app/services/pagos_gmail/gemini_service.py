"""
Gemini: enviar imagen o PDF en base64, extraer fecha_pago, cedula, monto, numero_referencia.
"""
import base64
import json
import logging
import re
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.pagos_gmail.helpers import get_mime_type

logger = logging.getLogger(__name__)

GEMINI_PROMPT = (
    "Este es un comprobante de pago (puede ser imagen o PDF). Extrae exactamente estos 4 datos en formato JSON: "
    "{ \"fecha_pago\": \"...\", \"cedula\": \"...\", \"monto\": \"...\", \"numero_referencia\": \"...\" } "
    "Si no encuentras algun dato, usa 'No encontrado'. Responde SOLO con el JSON, sin texto adicional."
)


def extract_payment_data(file_content: bytes, filename: str, api_key: Optional[str] = None) -> Dict[str, str]:
    """
    Envía el archivo a Gemini y devuelve dict con fecha_pago, cedula, monto, numero_referencia.
    """
    key = api_key or getattr(settings, "GEMINI_API_KEY", None)
    if not key:
        logger.warning(
            "[CONFIG] GEMINI_API_KEY no configurado. Configure la variable de entorno GEMINI_API_KEY "
            "(obtener en https://aistudio.google.com/apikey) para extraer datos de comprobantes."
        )
        return _empty_result("GEMINI_API_KEY no configurado")
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
    mime = get_mime_type(filename)
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name)
        part = {"inline_data": {"mime_type": mime, "data": base64.b64encode(file_content).decode("utf-8")}}
        response = model.generate_content([GEMINI_PROMPT, part])
        text = (response.text or "").strip()
        return _parse_gemini_json(text)
    except Exception as e:
        logger.exception("Gemini extract_payment_data: %s", e)
        return _empty_result(str(e))


def _parse_gemini_json(text: str) -> Dict[str, str]:
    """Extrae JSON del texto (puede venir con markdown o texto extra)."""
    default = {"fecha_pago": "No encontrado", "cedula": "No encontrado", "monto": "No encontrado", "numero_referencia": "No encontrado"}
    try:
        # Buscar bloque {...}
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return {
                "fecha_pago": str(data.get("fecha_pago", default["fecha_pago"])),
                "cedula": str(data.get("cedula", default["cedula"])),
                "monto": str(data.get("monto", default["monto"])),
                "numero_referencia": str(data.get("numero_referencia", default["numero_referencia"])),
            }
    except json.JSONDecodeError:
        pass
    return default


def _empty_result(reason: str) -> Dict[str, str]:
    return {"fecha_pago": "No encontrado", "cedula": "No encontrado", "monto": "No encontrado", "numero_referencia": reason}
