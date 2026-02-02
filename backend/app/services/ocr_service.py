"""
OCR sobre imagen de papeleta (Google Cloud Vision).
Extrae texto y trata de identificar: fecha, nombre_banco, numero_deposito, cantidad.
Si no se encuentra un campo, se devuelve "NA" para digitalización manual a partir del link.
"""
import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

NA = "NA"


def extract_from_image(image_bytes: bytes) -> Dict[str, str]:
    """
    Ejecuta OCR (Google Vision) sobre la imagen y devuelve:
    { "fecha_deposito", "nombre_banco", "numero_deposito", "cantidad" }.
    Cualquier campo no detectado se devuelve como "NA".
    """
    from app.core.informe_pagos_config_holder import get_google_credentials_json, sync_from_db
    sync_from_db()
    creds_json = get_google_credentials_json()
    if not creds_json:
        logger.warning("OCR: credenciales Google no configuradas.")
        return {"fecha_deposito": NA, "nombre_banco": NA, "numero_deposito": NA, "cantidad": NA}
    try:
        import json
        from google.oauth2 import service_account
        from google.cloud import vision

        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(creds_dict)
        client = vision.ImageAnnotatorClient(credentials=credentials)
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
