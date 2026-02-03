"""
Evalúa si la imagen de papeleta (vía texto OCR) es aceptable y genera una respuesta
corta y natural para WhatsApp: agradecer si es buena o pedir otra foto si es mala.
Usa OpenRouter con un prompt pequeño para una conversación corta.
"""
import json
import logging
from typing import Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.openrouter_client import call_openrouter
from app.models.configuracion import Configuracion

logger = logging.getLogger(__name__)

CLAVE_AI = "configuracion_ai"
MIN_CARACTERES_FALLBACK = 50

# Mensajes de respaldo si la IA no está configurada o falla (siempre explícitos: bien / mal / no es recibo)
MENSAJE_FALLBACK_GRACIAS = "La imagen está bien. Gracias. (Cédula {cedula} reportada.)"
MENSAJE_FALLBACK_MALA = "La imagen no es válida. Necesitamos un recibo de pago (papeleta de depósito), no un papel cualquiera. Envía una foto clara de tu papeleta a 20 cm."

SYSTEM_PROMPT = (
    "Eres un asistente de cobranza. Te dan el texto extraído por OCR de una foto que el cliente envió como comprobante de pago. "
    "Debes decidir si la imagen es ACEPTABLE como comprobante de pago o NO. "
    "ACEPTA como válido: papeleta de depósito bancario, recibo de pago, comprobante de venta, comprobante de transacción o cualquier documento legible que muestre monto, fecha y/o referencia de pago (ej. Banco Pichincha comprobante de venta, recibo de depósito, ticket de pago). "
    "NO aceptes: selfie, documento sin relación con pago (cédula sola, factura genérica sin monto), imagen borrosa ilegible, o papel que no sea un comprobante de pago. "
    "Responde ÚNICAMENTE con un JSON válido, sin markdown ni texto extra, con exactamente dos campos: "
    '"aceptable" (true o false) y "mensaje" (una sola frase corta en español). '
    "REGLAS para el mensaje: "
    "Si aceptable=true: el mensaje DEBE empezar o contener claramente que LA IMAGEN ESTÁ BIEN (ej. 'La imagen está bien. Gracias...' o 'Recibo válido. Gracias...'). "
    "Si aceptable=false: el mensaje DEBE decir claramente que LA IMAGEN NO ES VÁLIDA o NO ES UN COMPROBANTE DE PAGO (ej. 'La imagen no es válida...', 'Esto no es un comprobante de pago...'). Así el usuario sabe si está mal."
)


def _load_ai_config(db: Session) -> dict:
    """Carga api_key y modelo desde BD (configuracion_ai) o desde settings."""
    out = {
        "api_key": (getattr(settings, "OPENROUTER_API_KEY", None) or "").strip() or None,
        "model": (getattr(settings, "OPENROUTER_MODEL", None) or "openai/gpt-4o-mini").strip(),
        "temperature": 0.3,
        "max_tokens": 150,
    }
    try:
        row = db.get(Configuracion, CLAVE_AI)
        if row and row.valor:
            data = json.loads(row.valor)
            if isinstance(data, dict):
                if data.get("openrouter_api_key"):
                    out["api_key"] = str(data["openrouter_api_key"]).strip()
                if data.get("modelo"):
                    out["model"] = str(data["modelo"]).strip()
                if "temperatura" in data and data["temperatura"] is not None:
                    try:
                        out["temperature"] = float(data["temperatura"])
                    except (TypeError, ValueError):
                        pass
    except Exception as e:
        logger.debug("Carga config AI desde BD: %s", e)
    return out


def evaluar_imagen_y_respuesta(ocr_text: str, cedula: str, db: Session) -> Tuple[bool, str]:
    """
    Usa IA para evaluar si la imagen (texto OCR) es aceptable y genera una respuesta corta.
    Devuelve (aceptable, mensaje). Si la IA no está configurada o falla, usa fallback por cantidad de texto.
    """
    cfg = _load_ai_config(db)
    api_key = cfg.get("api_key")
    if not api_key:
        logger.debug("IA imagen: sin API key; usando fallback por OCR.")
        return _fallback_aceptable_y_mensaje(ocr_text, cedula)

    user_content = f"Texto OCR de la foto:\n{ocr_text[:2000] if ocr_text else '(vacío)'}\n\nCédula del cliente: {cedula or 'N/A'}. Responde solo el JSON."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    try:
        out = call_openrouter(
            messages=messages,
            api_key=api_key,
            model=cfg["model"],
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
        )
    except Exception as e:
        logger.warning("OpenRouter (imagen): %s", e)
        return _fallback_aceptable_y_mensaje(ocr_text, cedula)

    choices = out.get("choices") or []
    if not choices:
        return _fallback_aceptable_y_mensaje(ocr_text, cedula)
    content = (choices[0].get("message") or {}).get("content") or ""
    content = content.strip()
    # Quitar posible markdown de código
    if content.startswith("```"):
        lines = content.split("\n")
        if lines[0].strip() in ("```", "```json"):
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        obj = json.loads(content)
        aceptable = bool(obj.get("aceptable", False))
        mensaje = (obj.get("mensaje") or "").strip()
        if not mensaje:
            mensaje = MENSAJE_FALLBACK_GRACIAS.format(cedula=cedula or "N/A") if aceptable else MENSAJE_FALLBACK_MALA
        else:
            # Asegurar que el usuario siempre reciba feedback explícito: "está bien" / "no es válida" / "no es recibo"
            m_low = mensaje.lower()
            if aceptable and not any(x in m_low for x in ("bien", "válido", "valido", "gracias", "recibido")):
                mensaje = "La imagen está bien. " + mensaje
            elif not aceptable and not any(x in m_low for x in ("no es", "no válid", "inválid", "recibo", "papeleta", "papel cualquiera")):
                mensaje = "La imagen no es válida. " + mensaje
        return (aceptable, mensaje)
    except (json.JSONDecodeError, TypeError) as e:
        logger.debug("IA imagen: respuesta no es JSON válido: %s", e)
        return _fallback_aceptable_y_mensaje(ocr_text, cedula)


def _fallback_aceptable_y_mensaje(ocr_text: str, cedula: str) -> Tuple[bool, str]:
    """Fallback cuando no hay IA: aceptable si hay suficiente texto; mensajes fijos.
    Si no hay texto OCR (vacío o muy corto), aceptamos para no bloquear al usuario (p. ej. Vision no configurado)."""
    text = (ocr_text or "").strip()
    if len(text) < 20:
        # Sin texto OCR no podemos evaluar; no rechazar para que el documento "pase" y se procese
        return (True, MENSAJE_FALLBACK_GRACIAS.format(cedula=cedula or "N/A"))
    aceptable = len(text) >= MIN_CARACTERES_FALLBACK
    if aceptable:
        return (True, MENSAJE_FALLBACK_GRACIAS.format(cedula=cedula or "N/A"))
    return (False, MENSAJE_FALLBACK_MALA)


# --- Confirmación de datos (solo cédula, cantidad, número de documento) con IA ---
PROMPT_CONFIRMACION_DATOS = (
    "Eres un asistente de cobranza por WhatsApp. Acabas de recibir un comprobante de pago del cliente. "
    "Debes escribir UN SOLO mensaje corto y amable que: (1) confirme que recibiste el comprobante, "
    "(2) muestre estos tres datos que leímos: Cédula, Cantidad y Número de documento, "
    "(3) pida al cliente que responda SÍ para confirmar o que escriba las correcciones si algo está mal. "
    "Incluye los tres datos de forma clara (ej: Cédula: X, Cantidad: Y, Nº documento: Z). "
    "Tono cercano y profesional. Responde ÚNICAMENTE con el texto del mensaje, sin JSON ni markdown."
)


def generar_mensaje_confirmacion_datos(cedula: str, cantidad: str, numero_documento: str, db: Session) -> str:
    """
    Genera con IA un mensaje de conversación para que el cliente confirme solo estos datos:
    cédula, cantidad y número de documento. Si la IA falla, devuelve mensaje fijo con los 3 campos.
    """
    cfg = _load_ai_config(db)
    api_key = cfg.get("api_key")
    cedula = (cedula or "").strip() or "—"
    cantidad = (cantidad or "").strip() or "—"
    numero_documento = (numero_documento or "").strip() or "—"
    if cantidad.upper() == "NA":
        cantidad = "—"
    if numero_documento.upper() == "NA":
        numero_documento = "—"
    if not api_key:
        logger.debug("IA confirmación datos: sin API key, usando mensaje fijo")
        return _fallback_mensaje_confirmacion_datos(cedula, cantidad, numero_documento)
    logger.info("IA confirmación datos: generando mensaje para cedula=%s cantidad=%s nro_doc=%s", cedula[:6] + "***" if len(cedula or "") > 6 else cedula, cantidad, (numero_documento[:20] + "..." if len(numero_documento or "") > 20 else numero_documento))
    user_content = (
        f"Datos leídos del comprobante:\n- Cédula: {cedula}\n- Cantidad: {cantidad}\n- Número de documento: {numero_documento}\n\n"
        "Genera el mensaje para WhatsApp pidiendo confirmar o corregir solo estos tres datos."
    )
    messages = [
        {"role": "system", "content": PROMPT_CONFIRMACION_DATOS},
        {"role": "user", "content": user_content},
    ]
    try:
        out = call_openrouter(
            messages=messages,
            api_key=api_key,
            model=cfg["model"],
            temperature=0.4,
            max_tokens=280,
        )
        choices = out.get("choices") or []
        if choices:
            content = (choices[0].get("message") or {}).get("content") or ""
            msg = content.strip()
            if msg and len(msg) >= 30:
                return msg
    except Exception as e:
        logger.warning("OpenRouter (confirmación datos): %s", e, exc_info=True)
    logger.info("IA confirmación datos: usando fallback (IA no respondió o falló)")
    return _fallback_mensaje_confirmacion_datos(cedula, cantidad, numero_documento)


def _fallback_mensaje_confirmacion_datos(cedula: str, cantidad: str, numero_documento: str) -> str:
    """Mensaje fijo cuando la IA no está disponible."""
    return (
        "Recibimos tu comprobante. Estos son los datos que leímos:\n\n"
        f"• Cédula: {cedula}\n"
        f"• Cantidad: {cantidad}\n"
        f"• Nº documento: {numero_documento}\n\n"
        "Responde *SÍ* para confirmar o escribe las correcciones (ej: Cantidad 100.50, Nº documento 12345)."
    )
