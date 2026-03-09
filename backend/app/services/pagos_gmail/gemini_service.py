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
            "(obtener en https://aistudio.google.com/apikey) para extraer datos de comprobantes. "
            "El pipeline seguirá guardando filas con 'No encontrado' en los campos extraídos."
        )
        return _empty_result("GEMINI_API_KEY no configurado")
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
    logger.debug("[PAGOS_GMAIL] Gemini extrayendo datos de comprobante: %s (modelo %s)", filename, model_name)
    mime = get_mime_type(filename)
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name)
        part = {"inline_data": {"mime_type": mime, "data": base64.b64encode(file_content).decode("utf-8")}}
        # Reducir bloqueos por contenido "sensible" en comprobantes de pago
        safety = {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
        }
        try:
            response = model.generate_content(
                [GEMINI_PROMPT, part],
                generation_config=genai.types.GenerationConfig(temperature=0.1),
                safety_settings=list(safety.items()),
            )
        except TypeError:
            # Versiones antiguas pueden no aceptar safety_settings como list
            response = model.generate_content([GEMINI_PROMPT, part])
        text = (response.text or "").strip()
        return _parse_gemini_json(text)
    except Exception as e:
        logger.exception("Gemini extract_payment_data: %s", e)
        return _empty_result(str(e))


def _find_json_object(text: str) -> Optional[str]:
    """Encuentra el primer objeto JSON {...} en el texto (soporta valores con llaves)."""
    # Quitar posible markdown ```json ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```\s*$", "", text.strip())
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    quote = None
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if not in_string:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
            elif c in ('"', "'"):
                in_string = True
                quote = c
        elif c == quote:
            in_string = False
    return None


def _parse_gemini_json(text: str) -> Dict[str, str]:
    """Extrae JSON del texto (puede venir con markdown o texto extra)."""
    default = {"fecha_pago": "No encontrado", "cedula": "No encontrado", "monto": "No encontrado", "numero_referencia": "No encontrado"}
    try:
        json_str = _find_json_object(text)
        if not json_str:
            # Fallback: regex simple para JSON sin llaves en valores
            match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
            json_str = match.group(0) if match else None
        if json_str:
            data = json.loads(json_str)
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
