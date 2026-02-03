"""
OCR sobre imagen de recibo/factura/papeleta de depósito (Google Cloud Vision).
Usa DOCUMENT_TEXT_DETECTION, optimizado para documentos densos: texto manuscrito, impreso (letra tipo) o mixto.
Apto para: recibos, facturas, papeletas de depósito con una o ambas fuentes de texto.

Mapeo de campos:
  - Una fecha       → fecha de depósito
  - Cantidad        → total en dólares o bolívares (cantidad total)
  - Cédula          → viene del flujo WhatsApp (usuario la escribe)
  - Banco           → nombre en la cabecera del documento
Extrae además numero_deposito (referencia) y numero_documento (número de documento/recibo; formato variable: solo números, letras o mixto).
numero_documento se ubica por palabras clave configurables en Informe pagos (ej. "numero de documento", "numero de recibo"); si no hay config, se usan unas por defecto.
Si no se encuentra un campo, se devuelve "NA".
Regla HUMANO (evitar errores, no inventar): cuando más del 80% del texto detectado tiene confianza baja (manuscrito/ilegible), se devuelve humano="HUMANO" y todos los campos extraídos en NA; no se inventan datos.
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

# Mismo prefijo que whatsapp_service para buscar en Render.
# Diagnóstico: buscar "[INFORME_PAGOS]" (flujo) o "[INFORME_PAGOS] FALLO" (errores).
# Pasos OCR: 1/4=credenciales+cliente Vision, 2/4=document_text_detection, 3/4=texto extraído, 4/4=parse resultado.
LOG_TAG_INFORME = "[INFORME_PAGOS]"
LOG_TAG_FALLO = "[INFORME_PAGOS] FALLO"

NA = "NA"

MIN_CARACTERES_PARA_CLARA = 50  # Si el OCR detecta al menos esto, se considera imagen "suficientemente clara" (bajado de 80 para papeletas legibles)

# Regla HUMANO: si más del 80% del texto detectado tiene confianza baja (manuscrito/ilegible), se marca HUMANO y NO se inventan datos (campos NA).
UMBRAL_CONFIANZA_BAJA = 0.85  # Palabras con confidence < esto se consideran "baja confianza"
PORCENTAJE_MINIMO_PARA_HUMANO = 0.80  # Si (palabras baja confianza / total) >= esto → requiere revisión humana
VALOR_HUMANO = "HUMANO"  # Valor fijo para la columna HUMANO; no inventar cuando esté marcado

VISION_SCOPE = ["https://www.googleapis.com/auth/cloud-vision"]


def _get_vision_client():
    """Cliente de Vision API con credenciales (OAuth o cuenta de servicio). Devuelve None si no hay credenciales."""
    from app.core.informe_pagos_config_holder import sync_from_db
    from app.core.google_credentials import get_google_credentials
    from google.cloud import vision

    logger.info("%s [OCR] Paso 1/4: sync_from_db + get_google_credentials(Vision)", LOG_TAG_INFORME)
    sync_from_db()
    credentials = get_google_credentials(VISION_SCOPE)
    if not credentials:
        logger.warning(
            "%s [OCR] Paso 1/4 FALLO: credenciales Google (Vision) no disponibles. "
            "Comprueba Configuración > Informe pagos (JSON cuenta de servicio u OAuth con Conectar con Google).",
            LOG_TAG_FALLO,
        )
        return None
    try:
        client = vision.ImageAnnotatorClient(credentials=credentials)
        logger.info("%s [OCR] Paso 1/4 OK: cliente Vision creado", LOG_TAG_INFORME)
        return client
    except Exception as e:
        logger.exception("%s [OCR] Paso 1/4 FALLO: crear ImageAnnotatorClient: %s", LOG_TAG_FALLO, e)
        return None


def _vision_full_text(image_bytes: bytes) -> str:
    """Ejecuta Vision document_text_detection (documentos densos: manuscrito, impreso o mixto) y devuelve el texto completo; vacío si falla o sin credenciales."""
    client = _get_vision_client()
    if not client:
        logger.warning("%s [OCR] Vision no configurado (get_full_text); se tratará como no clara.", LOG_TAG_INFORME)
        return ""
    try:
        from google.cloud import vision
        image = vision.Image(content=image_bytes)
        logger.info("%s [OCR] Paso 2/4: document_text_detection llamando Vision API (bytes=%d)", LOG_TAG_INFORME, len(image_bytes or b""))
        response = client.document_text_detection(image=image)
        if response.error.message:
            code = getattr(response.error, "code", None)
            logger.warning(
                "%s [OCR] Paso 2/4 FALLO: Vision API devolvió error code=%s message=%s",
                LOG_TAG_FALLO, code, response.error.message,
            )
            return ""
        doc = response.full_text_annotation
        text = (doc.text if doc else "") or ""
        logger.info("%s [OCR] Paso 2/4 OK: Vision texto len=%d", LOG_TAG_INFORME, len(text))
        return text
    except Exception as e:
        logger.exception("%s [OCR] Paso 2/4 FALLO: document_text_detection exception: %s", LOG_TAG_FALLO, e)
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
        logger.info("%s [OCR] Claridad: imagen vacía o muy pequeña (bytes=%d); no clara", LOG_TAG_INFORME, len(image_bytes or b""))
        return False
    full_text = _vision_full_text(image_bytes)
    num_chars = len(full_text.strip())
    clara = num_chars >= min_chars
    logger.info("%s [OCR] Claridad: Vision %d caracteres (mín %d); clara=%s", LOG_TAG_INFORME, num_chars, min_chars, clara)
    return clara


def _requiere_revision_humana_from_doc(doc) -> bool:
    """Calcula si el documento requiere revisión humana (no inventar) a partir de full_text_annotation."""
    if not doc:
        return False
    total = 0
    baja_confianza = 0
    try:
        for page in doc.pages:
            for block in page.blocks:
                for para in block.paragraphs:
                    for word in para.words:
                        conf = getattr(word, "confidence", None)
                        if conf is not None:
                            total += 1
                            if conf < UMBRAL_CONFIANZA_BAJA:
                                baja_confianza += 1
    except (AttributeError, TypeError) as e:
        logger.debug("No se pudo calcular confianza OCR (usando doc.pages): %s", e)
        return False
    if total == 0:
        return False
    return (baja_confianza / total) >= PORCENTAJE_MINIMO_PARA_HUMANO


def extract_from_image(image_bytes: bytes) -> Dict[str, str]:
    """
    Ejecuta OCR (Google Vision) sobre la imagen y devuelve:
    - fecha_deposito, nombre_banco, numero_deposito, numero_documento, cantidad (o "NA" si no detectado)
    - humano: "HUMANO" si más del 80% del texto es de baja confianza (manuscrito/ilegible); en ese caso NO se inventan datos (todos los campos NA).
    """
    base_na = {"fecha_deposito": NA, "nombre_banco": NA, "numero_deposito": NA, "numero_documento": NA, "cantidad": NA}
    size = len(image_bytes or b"")
    logger.info("%s [OCR] extract_from_image INICIO | bytes=%d", LOG_TAG_INFORME, size)
    if size < 100:
        logger.warning("%s [OCR] extract_from_image: imagen demasiado pequeña (bytes=%d); devolviendo NA", LOG_TAG_FALLO, size)
        return {**base_na, "humano": ""}
    client = _get_vision_client()
    if not client:
        logger.warning(
            "%s %s | credenciales Vision no configuradas; todos los campos NA.",
            LOG_TAG_FALLO, "ocr",
        )
        return {**base_na, "humano": ""}
    try:
        from app.core.informe_pagos_config_holder import get_ocr_keywords_numero_documento
        from google.cloud import vision
        image = vision.Image(content=image_bytes)
        logger.info("%s [OCR] Paso 3/4: document_text_detection (extract)", LOG_TAG_INFORME)
        response = client.document_text_detection(image=image)
        if response.error.message:
            code = getattr(response.error, "code", None)
            logger.warning(
                "%s %s | Vision API error code=%s (habilitar Vision API y facturación en GCP): %s",
                LOG_TAG_FALLO, "ocr", code, response.error.message,
            )
            return {**base_na, "humano": ""}
        doc = response.full_text_annotation
        if _requiere_revision_humana_from_doc(doc):
            logger.info("%s OCR >80%% baja confianza → HUMANO (no inventar datos).", LOG_TAG_INFORME)
            return {**base_na, "humano": VALOR_HUMANO}
        full_text = (doc.text if doc else "") or ""
        logger.info("%s [OCR] Paso 3/4 OK: texto extraído len=%d preview=%s", LOG_TAG_INFORME, len(full_text), (full_text[:120] + "..." if len(full_text) > 120 else full_text))
        keywords_doc = get_ocr_keywords_numero_documento()
        result = _parse_papeleta_text(full_text, keywords_numero_documento=keywords_doc)
        result["humano"] = ""
        logger.info(
            "%s [OCR] Paso 4/4 parse resultado: fecha=%s banco=%s numero_dep=%s numero_doc=%s cantidad=%s",
            LOG_TAG_INFORME,
            result.get("fecha_deposito"),
            result.get("nombre_banco"),
            result.get("numero_deposito"),
            result.get("numero_documento"),
            result.get("cantidad"),
        )
        return result
    except Exception as e:
        logger.exception("%s %s | extract_from_image exception: %s", LOG_TAG_FALLO, "ocr", e)
        return {**base_na, "humano": ""}


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
