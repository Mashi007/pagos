"""
Escribe filas de informe de papeletas en Google Sheets.
Una pestaña por periodo (6am, 1pm, 4h30) o una sola pestaña si sheet_tab_principal está configurado.
Mapeo fijo A→I para que la información OCR se organice igual en todas las pestañas.
Usa OAuth o cuenta de servicio según informe_pagos_config.
"""
import logging
from typing import List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

LOG_TAG_INFORME = "[INFORME_PAGOS]"
LOG_TAG_FALLO = "[INFORME_PAGOS] FALLO"

# --- Mapeo Google Sheet (única fuente de verdad) ---
# Orden de columnas A(0) a I(8). Cualquier append/update debe usar este orden.
# Índice → (nombre_cabecera, campo_modelo_pagos_informe)
_MAPEO_COLUMNAS_SHEET = [
    (0, "Cédula", "cedula"),
    (1, "Fecha", "fecha_deposito"),
    (2, "Nombre en cabecera", "nombre_banco"),
    (3, "Número depósito", "numero_deposito"),
    (4, "Número de documento", "numero_documento"),
    (5, "Cantidad", "cantidad"),
    (6, "HUMANO", "humano"),
    (7, "Link imagen", "link_imagen"),
    (8, "Observación", "observacion"),
]
CABECERAS_INFORME = [cabecera for _, cabecera, _ in _MAPEO_COLUMNAS_SHEET]
NUM_COLUMNAS = len(CABECERAS_INFORME)  # 9 (A-I)

# Nombres de pestaña por periodo (6am, 1pm, 4h30). Si sheet_tab_principal está configurado, se usa esa pestaña para todo.
PERIODOS = {"6am": "6am", "1pm": "1pm", "4h30": "4h30"}
PESTAÑAS_VALIDAS = frozenset(("6am", "1pm", "4h30"))

SHEETS_SCOPE = ["https://www.googleapis.com/auth/spreadsheets"]


def _row_from_informe(informe: Any) -> List[str]:
    """Construye la fila de valores para Sheet en el orden A→I según _MAPEO_COLUMNAS_SHEET."""
    out: List[str] = []
    for _, _label, campo in _MAPEO_COLUMNAS_SHEET:
        val = getattr(informe, campo, None)
        if val is None:
            val = ""
        out.append((str(val).strip() if val else ""))
    return out


def _nombre_pestaña(periodo_envio: str, sheet_tab_principal: Optional[str]) -> str:
    """Devuelve el nombre de la pestaña donde escribir: sheet_tab_principal o 6am/1pm/4h30."""
    if sheet_tab_principal and (sheet_tab_principal or "").strip():
        return (sheet_tab_principal or "").strip()
    return PERIODOS.get((periodo_envio or "").strip()) or (periodo_envio or "6am").strip() or "6am"


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
    Añade una fila a la pestaña correspondiente. Orden de columnas A→I según CABECERAS_INFORME.
    Pestaña: sheet_tab_principal si está configurado; si no, 6am / 1pm / 4h30 según periodo_envio.
    Crea la pestaña si no existe y escribe la fila de cabecera.
    """
    from app.core.informe_pagos_config_holder import get_sheet_tab_principal

    service, sheet_id = _get_sheets_service()
    if not service or not sheet_id:
        logger.warning("%s %s | Sheets no configurado (ID hoja o credenciales/OAuth).", LOG_TAG_FALLO, "sheets")
        return False
    tab_principal = get_sheet_tab_principal()
    tab_name = _nombre_pestaña(periodo_envio or "", tab_principal)
    logger.info("%s Sheets append_row → pestaña '%s' (periodo=%s) | sheet_id=%s", LOG_TAG_INFORME, tab_name, periodo_envio, _mask_sheet_id(sheet_id))
    try:
        ensure_sheet_tab(sheet_id, tab_name)
        row = [
            (cedula or "").strip(),
            (fecha_deposito or "").strip(),
            (nombre_banco or "").strip(),
            (numero_deposito or "").strip(),
            (numero_documento or "").strip(),
            (cantidad or "").strip(),
            (humano or "").strip() or "",
            (link_imagen or "").strip(),
            (observacion or "").strip() or "",
        ]
        if len(row) != NUM_COLUMNAS:
            logger.warning("%s Sheets append_row: fila con %d columnas (esperado %d)", LOG_TAG_FALLO, len(row), NUM_COLUMNAS)
        range_name = _range_pestaña(tab_name)
        body = {"values": [row]}
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        logger.info("%s Sheets append_row OK | cedula=%s tab=%s", LOG_TAG_INFORME, (cedula or "").strip(), tab_name)
        return True
    except Exception as e:
        logger.exception("%s %s | Sheets append error (tab=%s): %s", LOG_TAG_FALLO, "sheets", tab_name, e)
        return False


def update_row_for_informe(informe: Any) -> bool:
    """
    Actualiza la misma fila en Google Sheets (no crea otra). Busca por link_imagen (col H).
    Usa el mismo mapeo A→I que append_row. Pestaña: sheet_tab_principal o 6am/1pm/4h30 por periodo_envio.
    """
    from app.core.informe_pagos_config_holder import get_sheet_tab_principal
    service, sheet_id = _get_sheets_service()
    if not service or not sheet_id:
        return False
    tab_principal = get_sheet_tab_principal()
    tab_name = _nombre_pestaña(informe.periodo_envio or "", tab_principal)
    informe_id = getattr(informe, "id", None)
    logger.info("%s Sheets update_row INICIO | informe_id=%s cedula=%s tab=%s", LOG_TAG_INFORME, informe_id, (informe.cedula or "").strip(), tab_name)
    try:
        range_all = _range_pestaña(tab_name, "A2:I")
        result = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=range_all).execute()
        rows = result.get("values") or []
        link = (informe.link_imagen or "").strip()
        cedula = (informe.cedula or "").strip()
        row_index = None
        for i, row in enumerate(rows):
            if len(row) < 8:
                continue
            col_h = (row[7] or "").strip()
            if link and (col_h == link or link in col_h or col_h.startswith(link[:50])):
                row_index = i + 2
                break
        if row_index is None and cedula:
            for i, row in enumerate(rows):
                if len(row) >= 1 and (row[0] or "").strip() == cedula:
                    if not link or (len(row) >= 8 and (row[7] or "").strip() == link):
                        row_index = i + 2
                        break
        if row_index is None:
            logger.warning("%s Sheets update_row: no se encontró fila en pestaña '%s'", LOG_TAG_INFORME, tab_name)
            return False
        row_values = _row_from_informe(informe)
        body = {"values": [row_values]}
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=_range_pestaña(tab_name, f"A{row_index}:I{row_index}"),
            valueInputOption="USER_ENTERED",
            body=body,
        ).execute()
        logger.info("%s Sheets update_row OK | cedula=%s tab=%s row=%s", LOG_TAG_INFORME, cedula, tab_name, row_index)
        return True
    except Exception as e:
        logger.exception("%s %s | Sheets update_row error: %s", LOG_TAG_FALLO, "sheets", e)
        return False


def _range_pestaña(tab_name: str, fila: Optional[str] = None) -> str:
    """Rango con pestaña entre comillas simples (p. ej. '6am'!A:I o 'Hoja 1'!A2:I)."""
    safe = (tab_name or "").replace("'", "''")
    if fila:
        return f"'{safe}'!{fila}"
    return f"'{safe}'!A:I"


def ensure_sheet_tab(sheet_id: str, tab_name: str, headers: Optional[List[str]] = None) -> bool:
    """
    Asegura que exista la pestaña con nombre tab_name y escribe la fila de cabecera A1:I1.
    Cabeceras = CABECERAS_INFORME (orden A→I). Si la pestaña ya existe, no sobrescribe.
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
            range=_range_pestaña(tab_name, "A1:I1"),
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
