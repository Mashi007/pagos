"""
OCR sobre imagen de papeleta (Google Cloud Vision).
Extrae texto y trata de identificar: fecha, nombre_banco, numero_deposito, cantidad.
Si no se encuentra un campo, se devuelve "NA" para digitalización manual a partir del link.
Usa OAuth o cuenta de servicio según informe_pagos_config.
"""
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

NA = "NA"

MIN_CARACTERES_PARA_CLARA = 50  # Si el OCR detecta al menos esto, se considera imagen "suficientemente clara" (bajado de 80 para papeletas legibles)

VISION_SCOPE = ["https://www.googleapis.com/auth/cloud-vision"]


def _get_vision_client():
    """Cliente de Vision API con credenciales (OAuth o cuenta de servicio). Devuelve None si no hay credenciales."""
    from app.core.informe_pagos_config_holder import sync_from_db
    from app.core.google_credentials import get_google_credentials
    from google.cloud import vision

    sync_from_db()
    credentials = get_google_credentials(VISION_SCOPE)
    if not credentials:
        return None
    return vision.ImageAnnotatorClient(credentials=credentials)


def _vision_full_text(image_bytes: bytes) -> str:
    """Ejecuta Vision text_detection y devuelve el texto completo; vacío si falla o sin credenciales."""
    client = _get_vision_client()
    if not client:
        logger.warning("Claridad de imagen no comprobada: credenciales Google (Vision) no configuradas; se tratará como no clara.")
        return ""
    try:
        from google.cloud import vision
        image = vision.Image(content=image_bytes)
        response = client.text_detection(image=image)
        if response.error.message:
            return ""
        texts = response.text_annotations
        return (texts[0].description if texts else "") or ""
    except Exception as e:
        logger.debug("Vision full_text: %s", e)
        return ""


def imagen_suficientemente_clara(image_bytes: bytes, min_chars: int = MIN_CARACTERES_PARA_CLARA) -> bool:
    """
    True si el OCR detecta al menos min_chars de texto (imagen legible).
    Se usa en el flujo de cobranza para aceptar la foto en el primer intento si está clara.
    """
    if not image_bytes or len(image_bytes) < 500:
        return False
    full_text = _vision_full_text(image_bytes)
    num_chars = len(full_text.strip())
    # Log para ajustar umbral: si no hay credenciales Google, full_text viene vacío y siempre "no clara"
    logger.debug("Claridad imagen: Vision devolvió %d caracteres (mínimo %d); clara=%s", num_chars, min_chars, num_chars >= min_chars)
    return num_chars >= min_chars


def extract_from_image(image_bytes: bytes) -> Dict[str, str]:
    """
    Ejecuta OCR (Google Vision) sobre la imagen y devuelve:
    { "fecha_deposito", "nombre_banco", "numero_deposito", "cantidad" }.
    Cualquier campo no detectado se devuelve como "NA".
    Usa OAuth o cuenta de servicio según informe_pagos_config.
    """
    client = _get_vision_client()
    if not client:
        logger.warning("OCR: credenciales Google (Vision) no configuradas.")
        return {"fecha_deposito": NA, "nombre_banco": NA, "numero_deposito": NA, "cantidad": NA}
    try:
        from google.cloud import vision
        image = vision.Image(content=image_bytes)
        response = client.text_detection(image=image)
        if response.error.message:
            logger.warning("Vision API error: %s", response.error.message)
            return {"fecha_deposito": NA, "nombre_banco": NA, "numero_deposito": NA, "cantidad": NA}
        texts = response.text_annotations
        full_text = (texts[0].description if texts else "") or ""
        return _parse_papeleta_text(full_text)
    except Exception as e:
        logger.exception("Error en OCR: %s", e)
        return {"fecha_deposito": NA, "nombre_banco": NA, "numero_deposito": NA, "cantidad": NA}


def _parse_papeleta_text(text: str) -> Dict[str, str]:
    """Heurística para extraer fecha, banco, número de depósito y cantidad del texto OCR."""
    result = {"fecha_deposito": NA, "nombre_banco": NA, "numero_deposito": NA, "cantidad": NA}
    if not text or not text.strip():
        return result
    lines = [ln.strip() for ln in text.replace("\r", "\n").split("\n") if ln.strip()]
    # Fecha: dd/mm/yyyy o dd-mm-yyyy o similar
    date_re = re.compile(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})\b")
    for line in lines:
        m = date_re.search(line)
        if m:
            result["fecha_deposito"] = f"{m.group(1)}/{m.group(2)}/{m.group(3)}"
            break
    # Cantidad: número con decimales (monto)
    amount_re = re.compile(r"\b(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\b")
    amounts = []
    for line in lines:
        for m in amount_re.finditer(line):
            s = m.group(1).replace(",", ".")
            if "." in s:
                parts = s.split(".")
                if len(parts) == 2 and len(parts[1]) == 2:
                    amounts.append(s)
    if amounts:
        result["cantidad"] = amounts[-1] if amounts else NA
    # Número de depósito/referencia: secuencia larga de dígitos
    ref_re = re.compile(r"\b(\d{10,})\b")
    for line in lines:
        m = ref_re.search(line)
        if m:
            result["numero_deposito"] = m.group(1)
            break
    # Banco: línea que contenga palabras típicas de banco (o segunda/tercera línea a veces es el nombre)
    bank_keywords = ["banco", "bank", "bancaria", "cuenta", "depósito", "transferencia"]
    for line in lines:
        lower = line.lower()
        if any(k in lower for k in bank_keywords) and len(line) >= 3:
            result["nombre_banco"] = line[:255]
            break
    if result["nombre_banco"] == NA and len(lines) >= 2:
        result["nombre_banco"] = lines[1][:255] if len(lines[1]) > 2 else NA
    return result
