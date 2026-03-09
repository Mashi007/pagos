"""
Gemini: enviar imagen o PDF en base64, extraer datos de comprobantes.
- Pagos (Gmail): fecha_pago, cedula, monto, numero_referencia.
- Cobranza (papeleta/informe): fecha_deposito, nombre_banco, numero_deposito, numero_documento, cantidad.
"""
import base64
import json
import logging
import re
import time
from typing import Any, Dict, Optional

# Reintento ante 429 (cuota/límite): esperar segundos sugeridos por la API o 45s por defecto
GEMINI_RATE_LIMIT_RETRY_DELAY = 45
GEMINI_RATE_LIMIT_MAX_RETRIES = 2

from app.core.config import settings
from app.services.pagos_gmail.helpers import get_mime_type

logger = logging.getLogger(__name__)

PAGOS_NA = "NA"  # No aplica: no hubo la información o al ser manual no se identifica

GEMINI_PROMPT = (
    "Eres un asistente especializado en leer comprobantes de pago venezolanos. "
    "La imagen puede ser un recibo bancario físico (BNC, Mercantil, Banesco, BDV, Bicentenario, Bancamiga, BOD), "
    "una captura de app bancaria, un comprobante de Pago Móvil, transferencia interbancaria, "
    "o pago en criptomoneda (USDT, Binance, etc.). "
    "Extrae estos 4 datos y responde ÚNICAMENTE con el JSON sin texto adicional:\n"
    "{\n"
    "  \"fecha_pago\": \"...\",\n"
    "  \"cedula\": \"...\",\n"
    "  \"monto\": \"...\",\n"
    "  \"numero_referencia\": \"...\"\n"
    "}\n\n"
    "REGLAS ESTRICTAS POR CAMPO:\n\n"
    "CEDULA:\n"
    "- Siempre empieza con V, E o J seguido de guion y números. Ejemplos: V-024691606, E-12345678, J-309841327.\n"
    "- Busca etiquetas: 'DP:V-', 'DP:E-', 'Cédula Dep.', 'C.I.', 'RIF', 'V-', 'E-', 'J-'.\n"
    "- Devuelve SOLO los dígitos sin prefijo (ej: si ves 'V-024691606' devuelve '024691606').\n"
    "- Si hay varias cédulas en la imagen, tomar la del PAGADOR/DEPOSITANTE (no la del beneficiario).\n\n"
    "MONTO:\n"
    "- Puede estar en bolívares (Bs, Bs., BsS) o dólares/divisas (Us$, USD, $, USDT).\n"
    "- Formato Bs venezolano usa punto como separador de miles y coma como decimal: '80.000,00 Bs' → devolver '80000.00 Bs'.\n"
    "- Incluir la moneda en el valor: '142.00 USD', '80000.00 Bs', '135 USDT', '260.00 USD'.\n"
    "- Busca: 'Deposito Us$', 'Monto', 'Monto (Bs.)', importe principal destacado visualmente.\n\n"
    "NUMERO_REFERENCIA (usar en este orden de prioridad según banco):\n"
    "- BNC: campo 'Ref:' (ej: Ref: 130611935 → devolver solo '130611935'). Si no está, usar 'Serial:'.\n"
    "- Mercantil: campo 'Serial:' (número largo, ej: Serial: 740087405431516 → devolver solo '740087405431516').\n"
    "- Banesco: campo 'Operación:' (ej: Operación: 3701189898485 → devolver solo '3701189898485').\n"
    "- Cualquier banco: 'ID de orden', 'Nro. de referencia', 'N° de referencia', 'NÚMERO DE REFERENCIA', "
    "'Número de operación', 'Código de operación', 'Nro. comprobante'.\n"
    "- Si hay varios números, preferir el más largo o el más prominente en el comprobante.\n"
    "- IMPORTANTE: devolver SOLO el número o código alfanumérico, SIN incluir la etiqueta "
    "(no escribir 'Ref:', 'Serial:', 'Operación:', etc., solo el valor).\n\n"
    "FECHA_PAGO:\n"
    "- Busca la fecha de la operación/transacción en cualquier formato (dd/mm/yyyy, yyyy-mm-dd, 'DD MAR YYYY').\n\n"
    "Si un dato genuinamente NO aparece en la imagen, usa 'NA'. Responde SOLO el JSON."
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
            "El pipeline seguirá guardando filas con 'NA' en los campos extraídos."
        )
        return _empty_result(PAGOS_NA)
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
    logger.warning("[PAGOS_GMAIL] Gemini → archivo=%s modelo=%s tamaño=%d bytes", filename, model_name, len(file_content))
    mime = get_mime_type(filename)
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name)
        part = {"inline_data": {"mime_type": mime, "data": base64.b64encode(file_content).decode("utf-8")}}
        last_error = None
        for attempt in range(GEMINI_RATE_LIMIT_MAX_RETRIES + 1):
            try:
                response = model.generate_content(
                    [GEMINI_PROMPT, part],
                    generation_config=genai.types.GenerationConfig(temperature=0.1),
                )
                # Verificar si la respuesta fue bloqueada por safety filters
                text = ""
                try:
                    text = (response.text or "").strip()
                except Exception as text_err:
                    # response.text lanza ValueError si fue bloqueado o no tiene partes de texto
                    candidates = getattr(response, "candidates", [])
                    finish_reasons = [str(getattr(c, "finish_reason", "?")) for c in candidates]
                    safety_ratings = []
                    for c in candidates:
                        for r in getattr(c, "safety_ratings", []):
                            safety_ratings.append(f"{r.category}={r.probability}")
                    logger.warning("[PAGOS_GMAIL] Gemini respuesta bloqueada/vacía para %s: %s | finish_reasons=%s | safety=%s",
                        filename, text_err, finish_reasons, safety_ratings)
                    return _empty_result(f"blocked: {text_err}")

                logger.warning("[PAGOS_GMAIL] Gemini raw(%s): %s", filename, text[:400] if text else "(VACÍO)")
                result = _parse_gemini_json(text)
                all_na = all(v == PAGOS_NA for v in result.values())
                if all_na:
                    logger.warning("[PAGOS_GMAIL] Gemini TODO NA para %s — respuesta completa: %s", filename, text[:300])
                else:
                    logger.warning("[PAGOS_GMAIL] Gemini OK: fecha=%s cedula=%s monto=%s ref=%s",
                        result.get("fecha_pago"), result.get("cedula"),
                        result.get("monto"), result.get("numero_referencia"))
                return result
            except Exception as e:
                last_error = e
                if _is_rate_limit_error(e) and attempt < GEMINI_RATE_LIMIT_MAX_RETRIES:
                    delay = _extract_retry_seconds(e)
                    logger.warning("[PAGOS_GMAIL] Gemini 429 (cuota), reintento en %ds (intento %d/%d)", delay, attempt + 1, GEMINI_RATE_LIMIT_MAX_RETRIES + 1)
                    time.sleep(delay)
                else:
                    raise
        return _empty_result(str(last_error))
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


def _normalize_to_na(val: Any) -> str:
    """Convierte a NA si está vacío, es 'No encontrado' o no se identifica claramente.
    Para numero_referencia también elimina etiquetas residuales como 'Ref:', 'Serial:', etc.
    """
    if val is None:
        return PAGOS_NA
    s = str(val).strip()
    if not s or s.lower() in ("no encontrado", "n/a", "n.a.", "-", "—", "na"):
        return PAGOS_NA
    # Eliminar etiquetas bancarias residuales que Gemini pueda incluir antes del número
    import re as _re
    s = _re.sub(
        r"^(Ref|Serial|Operaci[oó]n|N[°º]?\s*de\s*(referencia|operaci[oó]n|transferencia)|"
        r"ID\s*de\s*orden|N[°º]mero\s*de\s*referencia|NÚMERO\s*DE\s*REFERENCIA|"
        r"Nro\.?\s*de\s*referencia|C[oó]digo\s*de\s*operaci[oó]n|Nro\.?\s*comprobante)"
        r"\s*[:\-]?\s*",
        "", s, flags=_re.IGNORECASE,
    ).strip()
    # Eliminar también texto entre paréntesis al final: "130611935 (Ref:)" → "130611935"
    s = _re.sub(r"\s*\(.*?\)\s*$", "", s).strip()
    if not s:
        return PAGOS_NA
    return s


def _parse_gemini_json(text: str) -> Dict[str, str]:
    """Extrae JSON del texto (puede venir con markdown o texto extra). Normaliza vacíos/No encontrado a NA."""
    default = {"fecha_pago": PAGOS_NA, "cedula": PAGOS_NA, "monto": PAGOS_NA, "numero_referencia": PAGOS_NA}
    try:
        json_str = _find_json_object(text)
        if not json_str:
            match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
            json_str = match.group(0) if match else None
        if json_str:
            data = json.loads(json_str)
            return {
                "fecha_pago": _normalize_to_na(data.get("fecha_pago", default["fecha_pago"])),
                "cedula": _normalize_to_na(data.get("cedula", default["cedula"])),
                "monto": _normalize_to_na(data.get("monto", default["monto"])),
                "numero_referencia": _normalize_to_na(data.get("numero_referencia", default["numero_referencia"])),
            }
    except json.JSONDecodeError:
        pass
    return default.copy()


def _empty_result(reason: str = "") -> Dict[str, str]:
    if reason:
        logger.debug("[PAGOS_GMAIL] Gemini sin datos: %s", reason)
    return {"fecha_pago": PAGOS_NA, "cedula": PAGOS_NA, "monto": PAGOS_NA, "numero_referencia": PAGOS_NA}


# --- Cobranza: papeleta de depósito / comprobante (mismo formato que ocr_service para poder sustituir Vision)
COBRANZA_NA = "NA"
GEMINI_COBRANZA_PROMPT = (
    "Esta imagen es una papeleta de depósito, recibo de pago o comprobante bancario. "
    "Extrae exactamente estos campos en formato JSON (usa 'NA' si no encuentras el dato): "
    '"fecha_deposito" (fecha del depósito, formato dd/mm/yyyy o yyyy-mm-dd), '
    '"nombre_banco" (nombre del banco o institución financiera), '
    '"numero_deposito" (número de depósito, referencia o transacción, muchos dígitos), '
    '"numero_documento" (número de documento, recibo o comprobante de venta), '
    '"cantidad" (monto total en números, ej. 150.00 o 1.234,56), '
    '"aceptable" (true si el documento es claramente un comprobante de pago legible; false si está ilegible o no es comprobante). '
    "Responde SOLO con el JSON, sin texto adicional ni markdown."
)


def extract_cobranza_from_image(
    image_bytes: bytes,
    filename: str = "image.jpg",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Toma la imagen (papeleta/comprobante) y extrae información de cobranza con Gemini.
    Devuelve el mismo esquema que ocr_service.extract_from_image para poder usarse en el flujo de informe/cobranza:
    fecha_deposito, nombre_banco, numero_deposito, numero_documento, cantidad, humano, confianza_media.
    Si aceptable=false en la respuesta, se marca humano='HUMANO' para revisión.
    """
    key = api_key or getattr(settings, "GEMINI_API_KEY", None)
    base_na = {
        "fecha_deposito": COBRANZA_NA,
        "nombre_banco": COBRANZA_NA,
        "numero_deposito": COBRANZA_NA,
        "numero_documento": COBRANZA_NA,
        "cantidad": COBRANZA_NA,
        "humano": "",
        "confianza_media": 0.0,
    }
    if not key or not str(key).strip():
        logger.warning("[COBRANZA] GEMINI_API_KEY no configurado; no se puede extraer información de cobranza desde imagen.")
        return base_na
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
    mime = get_mime_type(filename)
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name)
        part = {"inline_data": {"mime_type": mime, "data": base64.b64encode(image_bytes).decode("utf-8")}}
        safety = {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
        }
        last_error = None
        for attempt in range(GEMINI_RATE_LIMIT_MAX_RETRIES + 1):
            try:
                response = model.generate_content(
                    [GEMINI_COBRANZA_PROMPT, part],
                    generation_config=genai.types.GenerationConfig(temperature=0.1),
                    safety_settings=safety,
                )
                text = (response.text or "").strip()
                return _parse_cobranza_json(text)
            except Exception as e:
                last_error = e
                if _is_rate_limit_error(e) and attempt < GEMINI_RATE_LIMIT_MAX_RETRIES:
                    delay = _extract_retry_seconds(e)
                    logger.warning("[COBRANZA] Gemini 429, reintento en %ds", delay)
                    time.sleep(delay)
                else:
                    raise
        return base_na
    except Exception as e:
        logger.exception("Gemini extract_cobranza_from_image: %s", e)
        return base_na


def _parse_cobranza_json(text: str) -> Dict[str, Any]:
    """Parsea la respuesta JSON de Gemini para cobranza; devuelve formato compatible con ocr_service."""
    base = {
        "fecha_deposito": COBRANZA_NA,
        "nombre_banco": COBRANZA_NA,
        "numero_deposito": COBRANZA_NA,
        "numero_documento": COBRANZA_NA,
        "cantidad": COBRANZA_NA,
        "humano": "",
        "confianza_media": 0.9,
    }
    try:
        json_str = _find_json_object(text)
        if not json_str:
            json_str = re.search(r"\{[^{}]*\}", text, re.DOTALL)
            json_str = json_str.group(0) if json_str else None
        if not json_str:
            return base
        data = json.loads(json_str)
        for k in ("fecha_deposito", "nombre_banco", "numero_deposito", "numero_documento", "cantidad"):
            v = data.get(k)
            if v is not None and str(v).strip():
                base[k] = str(v).strip()[:255] if k == "nombre_banco" else str(v).strip()[:100]
        aceptable = data.get("aceptable", True)
        if aceptable is False:
            base["humano"] = "HUMANO"
        return base
    except (json.JSONDecodeError, TypeError):
        return base


def _is_rate_limit_error(exc: Exception) -> bool:
    msg = (getattr(exc, "message", "") or str(exc)) if exc else ""
    return "429" in msg or "quota" in msg.lower() or "rate" in msg.lower()


def _extract_retry_seconds(exc: Exception) -> int:
    """Extrae 'retry in Xs' del mensaje de error de Gemini (429)."""
    msg = (getattr(exc, "message", "") or str(exc)) if exc else ""
    m = re.search(r"retry\s+in\s+([\d.]+)\s*s", msg, re.IGNORECASE)
    if m:
        return max(1, int(float(m.group(1))))
    return GEMINI_RATE_LIMIT_RETRY_DELAY


def check_gemini_available() -> Dict[str, Any]:
    """
    Test indirecto de Gemini: envía un prompt de texto simple (sin imagen) para verificar
    que la API key es válida y el servicio responde. Ante 429 (cuota) reintenta una vez tras esperar.
    Returns: {"ok": True} o {"ok": False, "error": "mensaje"}.
    """
    key = getattr(settings, "GEMINI_API_KEY", None)
    if not key or not str(key).strip():
        return {"ok": False, "error": "GEMINI_API_KEY no configurado"}
    model_name = getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel(model_name)
        last_error = None
        for attempt in range(GEMINI_RATE_LIMIT_MAX_RETRIES + 1):
            try:
                response = model.generate_content("Responde únicamente con la palabra OK, nada más.")
                text = (response.text or "").strip()
                if text:
                    return {"ok": True, "model": model_name, "response_preview": text[:50]}
                return {"ok": False, "error": "Gemini no devolvió texto"}
            except Exception as e:
                last_error = e
                if _is_rate_limit_error(e) and attempt < GEMINI_RATE_LIMIT_MAX_RETRIES:
                    delay = _extract_retry_seconds(e)
                    logger.warning("[PAGOS_GMAIL] Gemini 429 en health check, reintento en %ds", delay)
                    time.sleep(delay)
                else:
                    raise
        return {"ok": False, "error": str(last_error)}
    except Exception as e:
        logger.exception("Gemini check_gemini_available: %s", e)
        return {"ok": False, "error": str(e)}
