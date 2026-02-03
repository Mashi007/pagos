"""
OCR sobre imagen de papeleta (Google Cloud Vision).
Mapeo de campos:
  - Una fecha       → fecha de depósito
  - Cantidad        → total en dólares o bolívares (cantidad total)
  - Cédula          → viene del flujo WhatsApp (usuario la escribe)
  - Banco           → nombre en la cabecera del documento
Extrae además numero_deposito (referencia) y numero_documento (número de documento/recibo; formato variable: solo números, letras o mixto).
numero_documento se ubica por palabras clave configurables en Informe pagos (ej. "numero de documento", "numero de recibo"); si no hay config, se usan unas por defecto.
Si no se encuentra un campo, se devuelve "NA".
Usa OAuth o cuenta de servicio según informe_pagos_config.

Requisitos para que el proceso OCR funcione:
  1. Credenciales Google configuradas en Configuración > Informe pagos (cuenta de servicio JSON o OAuth).
  2. Cloud Vision API habilitada en el proyecto de Google Cloud.
  3. Facturación activa en el proyecto (Vision requiere cuenta de facturación vinculada).
  4. Mapeo a columnas: fecha_deposito→Sheet Fecha, nombre_banco→Nombre en cabecera, numero_deposito→Número depósito, cantidad→Cantidad; cédula y link_imagen/observación vienen del flujo.
"""
import re
import logging
from typing import Dict, Any, List, Optional

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


def get_full_text(image_bytes: bytes) -> str:
    """Texto completo extraído por OCR (Vision). Para uso por IA de respuesta de imagen."""
    return _vision_full_text(image_bytes or b"")


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
    - fecha_deposito: fecha de depósito
    - nombre_banco: nombre en la cabecera (banco/institución)
    - numero_deposito: referencia/depósito
    - cantidad: cantidad total en dólares o bolívares
    Cualquier campo no detectado se devuelve como "NA".
    """
    client = _get_vision_client()
    if not client:
        logger.warning("OCR: credenciales Google (Vision) no configuradas.")
        return {"fecha_deposito": NA, "nombre_banco": NA, "numero_deposito": NA, "numero_documento": NA, "cantidad": NA}
    try:
        from app.core.informe_pagos_config_holder import get_ocr_keywords_numero_documento
        from google.cloud import vision
        image = vision.Image(content=image_bytes)
        response = client.text_detection(image=image)
        if response.error.message:
            logger.warning("Vision API error: %s", response.error.message)
            return {"fecha_deposito": NA, "nombre_banco": NA, "numero_deposito": NA, "numero_documento": NA, "cantidad": NA}
        texts = response.text_annotations
        full_text = (texts[0].description if texts else "") or ""
        keywords_doc = get_ocr_keywords_numero_documento()
        return _parse_papeleta_text(full_text, keywords_numero_documento=keywords_doc)
    except Exception as e:
        logger.exception("Error en OCR: %s", e)
        return {"fecha_deposito": NA, "nombre_banco": NA, "numero_deposito": NA, "numero_documento": NA, "cantidad": NA}


def _parse_papeleta_text(text: str, keywords_numero_documento: Optional[list] = None) -> Dict[str, str]:
    """
    Extrae del texto OCR según mapeo:
    - fecha_deposito: una fecha = fecha de depósito (etiqueta Fecha/Date o patrón dd/mm/yyyy)
    - cantidad: cantidad total en dólares o bolívares (línea Total o último monto con decimales)
    - nombre_banco: banco = nombre en la cabecera (primeras líneas o línea con BANCO/institución)
    - numero_deposito: número de referencia/depósito
    - numero_documento: número de documento/recibo; formato variable (números, letras o mixto); se ubica por palabras clave (keywords_numero_documento)
    La cédula no se extrae aquí; viene del flujo WhatsApp (usuario la escribe).
    """
    result = {"fecha_deposito": NA, "nombre_banco": NA, "numero_deposito": NA, "numero_documento": NA, "cantidad": NA}
    if not text or not text.strip():
        return result
    lines = [ln.strip() for ln in text.replace("\r", "\n").split("\n") if ln.strip()]

    # --- Fecha = fecha de depósito: dd/mm/yyyy o etiqueta "Fecha:" / "Date:"; año 2 dígitos → 4
    def _normalize_date(d: str, m: str, y: str) -> str:
        yy = y
        if len(y) == 2:
            yi = int(y)
            yy = str(2000 + yi) if yi <= 30 else str(1900 + yi)
        return f"{d}/{m}/{yy}"

    date_re = re.compile(r"\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})\b")
    for line in lines[:15]:
        lower = line.lower()
        if "fecha" in lower or "date" in lower:
            m = date_re.search(line)
            if m:
                result["fecha_deposito"] = _normalize_date(m.group(1), m.group(2), m.group(3))
                break
    if result["fecha_deposito"] == NA:
        for line in lines:
            m = date_re.search(line)
            if m:
                result["fecha_deposito"] = _normalize_date(m.group(1), m.group(2), m.group(3))
                break

    # --- Cantidad = total en dólares o bolívares: línea "Total"/"TOTAL" o último monto con $/Bs
    amount_re = re.compile(r"[\$Bs\.]?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:USD|Bs\.?|\$)?", re.I)
    total_amount = None
    for i, line in enumerate(lines):
        lower = line.lower()
        if "total" in lower and ("subtotal" not in lower and "iva" not in lower):
            for m in amount_re.finditer(line):
                s = m.group(1).replace(",", ".")
                if "." in s and len(s.split(".")[-1]) == 2:
                    total_amount = s
                    break
            if total_amount:
                break
    if not total_amount:
        for line in lines:
            for m in amount_re.finditer(line):
                s = m.group(1).replace(",", ".")
                if "." in s and len(s.split(".")[-1]) == 2:
                    total_amount = s
        if total_amount:
            result["cantidad"] = total_amount
    else:
        result["cantidad"] = total_amount
    if result["cantidad"] == NA:
        # Fallback: último número con dos decimales
        for line in reversed(lines):
            for m in re.finditer(r"\b(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\b", line):
                s = m.group(1).replace(",", ".")
                if "." in s and len(s.split(".")[-1]) == 2:
                    result["cantidad"] = s
                    break
            if result["cantidad"] != NA:
                break

    # --- Banco = nombre en la cabecera: primeras líneas o línea que contenga BANCO/institución
    bank_keywords = ["banco", "bank", "bancaria", "c.a.", "ca ", "s.a.", "sa "]
    for line in lines[:5]:
        if not line or len(line) < 4:
            continue
        lower = line.lower()
        if any(k in lower for k in bank_keywords):
            result["nombre_banco"] = line[:255]
            break
        if len(line) >= 8 and len(line) <= 120 and not re.match(r"^\d[\d\s.,]*$", line):
            result["nombre_banco"] = line[:255]
            break
    if result["nombre_banco"] == NA and len(lines) >= 1 and len(lines[0]) > 2:
        result["nombre_banco"] = lines[0][:255]

    # --- Número de depósito/referencia: preferir línea con ref/referencia/depósito/nº; luego cualquier 10+ dígitos
    ref_re = re.compile(r"\b(\d{10,})\b")
    ref_keywords = ["ref", "referencia", "depósito", "deposito", "nº", "no.", "nro", "número", "numero"]
    for line in lines:
        lower = line.lower()
        if any(k in lower for k in ref_keywords):
            m = ref_re.search(line)
            if m:
                result["numero_deposito"] = m.group(1)
                break
    if result["numero_deposito"] == NA:
        for line in lines:
            m = ref_re.search(line)
            if m:
                result["numero_deposito"] = m.group(1)
                break

    # --- Número de documento/recibo: formato variable (solo números, letras o mixto); se ubica por palabras clave configurables
    keywords_doc = keywords_numero_documento or []
    for line in lines:
        if not line or result["numero_documento"] != NA:
            break
        lower = line.lower()
        for kw in keywords_doc:
            if kw and kw.lower() in lower:
                idx_colon = line.find(":")
                if idx_colon >= 0:
                    val = line[idx_colon + 1 :].strip()
                else:
                    idx_kw = lower.find(kw.lower())
                    val = (line[idx_kw + len(kw) :].strip() if idx_kw >= 0 else "").strip()
                val = re.sub(r"^\s*[:\-]\s*", "", val)
                if val and len(val) >= 1:
                    result["numero_documento"] = val[:100].strip()
                    break
                break
        if result["numero_documento"] != NA:
            break

    return result
