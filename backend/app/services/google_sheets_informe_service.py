"""
Escribe filas de informe de papeletas en Google Sheets.
Una pestaña por periodo (6am, 1pm, 4h30).
Cabeceras: Cédula, Fecha (fecha de depósito), Nombre en cabecera (banco), Número depósito, Cantidad (total USD/Bs), Link imagen, Observación.
Usa OAuth o cuenta de servicio según informe_pagos_config.
"""
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

LOG_TAG_INFORME = "[INFORME_PAGOS]"
LOG_TAG_FALLO = "[INFORME_PAGOS] FALLO"

# Nombres de pestaña por periodo (clave interna)
PERIODOS = {"6am": "6am", "1pm": "1pm", "4h30": "4h30"}

# Columnas del informe (orden A→I). Origen de cada una para no dejar ninguna sin ubicar:
#  A Cédula             → flujo WhatsApp (usuario escribe)
#  B Fecha              → fecha de depósito (OCR)
#  C Nombre en cabecera → banco, nombre en la cabecera del documento (OCR)
#  D Número depósito    → referencia/depósito (OCR)
#  E Número de documento → número doc/recibo; formato variable; OCR por palabras clave configurables
#  F Cantidad           → total en dólares o bolívares (OCR)
#  G HUMANO             → "HUMANO" cuando >80% del texto es de baja confianza (manuscrito/ilegible); no se inventan datos
#  H Link imagen        → URL de la imagen en Google Drive
#  I Observación        → ej. "No confirma identidad" (flujo WhatsApp)
CABECERAS_INFORME = ["Cédula", "Fecha", "Nombre en cabecera", "Número depósito", "Número de documento", "Cantidad", "HUMANO", "Link imagen", "Observación"]

SHEETS_SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]


def _mask_sheet_id(sheet_id: str) -> str:
    """Muestra solo últimos 4 caracteres del ID para logs (evitar exponer ID completo)."""
    if not sheet_id or len(sheet_id) <= 4:
        return "****"
    return f"...{sheet_id[-4:]}"


def _get_sheets_service():
    """Construye el cliente de Google Sheets con credenciales (OAuth o cuenta de servicio)."""
    from app.core.informe_pagos_config_holder import get_google_sheets_id, sync_from_db
    from app.core.google_credentials import get_google_credentials
    from googleapiclient.discovery import build

    sync_from_db()
    sheet_id = get_google_sheets_id()
    credentials = get_google_credentials(SHEETS_SCOPE)
    if not credentials:
        logger.warning("%s Sheets: credenciales no configuradas (OAuth o cuenta de servicio).", LOG_TAG_FALLO)
        return None, None
    if not sheet_id:
        logger.warning("%s Sheets: google_sheets_id vacío. Configura el ID en Informe pagos (desde la URL de la hoja).", LOG_TAG_FALLO)
        return None, None
    try:
        service = build("sheets", "v4", credentials=credentials)
        return service, sheet_id
    except Exception as e:
        logger.exception("%s Sheets: error al crear cliente: %s", LOG_TAG_FALLO, e)
        return None, None


def append_row(
    cedula: str,
    fecha_deposito: str,
    nombre_banco: str,
    numero_deposito: str,
    numero_documento: str,
    cantidad: str,
    link_imagen: str,
    periodo_envio: str,
    observacion: Optional[str] = None,
    humano: Optional[str] = None,
) -> bool:
    """
    Añade una fila a la pestaña configurada.
    Si sheet_tab_principal está configurado (ej. "Hoja 1"), se escribe ahí; si no, se usa la pestaña del periodo (6am, 1pm, 4h30).
    Crea la pestaña si no existe (cabeceras incluyen HUMANO).
    """
    from app.core.informe_pagos_config_holder import get_sheet_tab_principal

    service, sheet_id = _get_sheets_service()
    if not service or not sheet_id:
        logger.warning("%s %s | Sheets no configurado (ID hoja o credenciales/OAuth).", LOG_TAG_FALLO, "sheets")
        return False
    tab_principal = get_sheet_tab_principal()
    if tab_principal:
        tab_name = tab_principal
        logger.info("%s Sheets append_row → pestaña '%s' (sheet_tab_principal) | sheet_id=%s", LOG_TAG_INFORME, tab_name, _mask_sheet_id(sheet_id))
    else:
        tab_name = PERIODOS.get(periodo_envio) or periodo_envio
        logger.info("%s Sheets append_row → pestaña '%s' (periodo %s) | sheet_id=%s", LOG_TAG_INFORME, tab_name, periodo_envio, _mask_sheet_id(sheet_id))
    try:
        ensure_sheet_tab(sheet_id, tab_name)
        range_name = f"'{tab_name}'!A:I"
        obs = (observacion or "").strip() or ""
        humano_val = (humano or "").strip() or ""
        body = {"values": [[cedula, fecha_deposito, nombre_banco, numero_deposito, numero_documento or "", cantidad, humano_val, link_imagen, obs]]}
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        logger.info("%s Sheets append_row OK | cedula=%s tab=%s", LOG_TAG_INFORME, cedula, tab_name)
        return True
    except Exception as e:
        logger.exception("%s %s | Sheets append error (tab=%s): %s", LOG_TAG_FALLO, "sheets", tab_name, e)
        return False


def ensure_sheet_tab(sheet_id: str, tab_name: str, headers: Optional[List[str]] = None) -> bool:
    """
    Asegura que exista la pestaña con nombre tab_name y opcionalmente la fila de cabecera.
    headers: Cédula, Fecha, Nombre en cabecera, Número depósito, Número de documento, Cantidad, HUMANO, Link imagen, Observación.
    """
    service, _ = _get_sheets_service()
    if not service:
        return False
    if headers is None:
        headers = CABECERAS_INFORME
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheet_titles = [s.get("properties", {}).get("title") for s in spreadsheet.get("sheets", [])]
        if tab_name in sheet_titles:
            return True
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": tab_name}}}]},
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"'{tab_name}'!A1:I1",
            valueInputOption="USER_ENTERED",
            body={"values": [headers]},
        ).execute()
        return True
    except Exception as e:
        logger.exception("%s %s | Sheets ensure_sheet_tab error: %s", LOG_TAG_FALLO, "sheets", e)
        return False


def get_sheet_link_for_period(periodo_envio: str) -> Optional[str]:
    """Devuelve la URL de la hoja (con foco en la pestaña si la API lo permite)."""
    from app.core.informe_pagos_config_holder import get_google_sheets_id, sync_from_db
    sync_from_db()
    sheet_id = get_google_sheets_id()
    if not sheet_id:
        return None
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"
