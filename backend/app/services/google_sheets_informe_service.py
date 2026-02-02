"""
Escribe filas de informe de papeletas en Google Sheets.
Una pestaña por periodo (6am, 1pm, 4h30). Columnas: Cédula, Fecha, Nombre banco, Número depósito, Cantidad, Link imagen, Observación.
"""
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Nombres de pestaña por periodo (clave interna)
PERIODOS = {"6am": "6am", "1pm": "1pm", "4h30": "4h30"}


def _get_sheets_service():
    """Construye el cliente de Google Sheets con credenciales del config."""
    from app.core.informe_pagos_config_holder import get_google_credentials_json, get_google_sheets_id, sync_from_db
    import json
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    sync_from_db()
    creds_json = get_google_credentials_json()
    sheet_id = get_google_sheets_id()
    if not creds_json or not sheet_id:
        return None, None
    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
    service = build("sheets", "v4", credentials=credentials)
    return service, sheet_id


def append_row(
    cedula: str,
    fecha_deposito: str,
    nombre_banco: str,
    numero_deposito: str,
    cantidad: str,
    link_imagen: str,
    periodo_envio: str,
    observacion: Optional[str] = None,
) -> bool:
    """
    Añade una fila a la pestaña del periodo en la hoja configurada.
    periodo_envio: "6am" | "1pm" | "4h30"
    observacion: ej. "No confirma identidad" si no confirmó en 3 intentos.
    Crea la pestaña si no existe (con cabeceras: Cédula, Fecha, Nombre banco, Número depósito, Cantidad, Link imagen, Observación).
    """
    service, sheet_id = _get_sheets_service()
    if not service or not sheet_id:
        logger.warning("Google Sheets no configurado.")
        return False
    tab_name = PERIODOS.get(periodo_envio) or periodo_envio
    try:
        ensure_sheet_tab(sheet_id, tab_name)
        range_name = f"'{tab_name}'!A:G"
        obs = (observacion or "").strip() or ""
        body = {"values": [[cedula, fecha_deposito, nombre_banco, numero_deposito, cantidad, link_imagen, obs]]}
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        return True
    except Exception as e:
        logger.exception("Error escribiendo en Google Sheets: %s", e)
        return False


def ensure_sheet_tab(sheet_id: str, tab_name: str, headers: Optional[List[str]] = None) -> bool:
    """
    Asegura que exista la pestaña con nombre tab_name y opcionalmente la fila de cabecera.
    headers: ["Cédula", "Fecha", "Nombre banco", "Número depósito", "Cantidad", "Link imagen", "Observación"]
    """
    service, _ = _get_sheets_service()
    if not service:
        return False
    if headers is None:
        headers = ["Cédula", "Fecha", "Nombre banco", "Número depósito", "Cantidad", "Link imagen", "Observación"]
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
            range=f"'{tab_name}'!A1:G1",
            valueInputOption="USER_ENTERED",
            body={"values": [headers]},
        ).execute()
        return True
    except Exception as e:
        logger.exception("Error creando pestaña en Sheets: %s", e)
        return False


def get_sheet_link_for_period(periodo_envio: str) -> Optional[str]:
    """Devuelve la URL de la hoja (con foco en la pestaña si la API lo permite)."""
    from app.core.informe_pagos_config_holder import get_google_sheets_id, sync_from_db
    sync_from_db()
    sheet_id = get_google_sheets_id()
    if not sheet_id:
        return None
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"
