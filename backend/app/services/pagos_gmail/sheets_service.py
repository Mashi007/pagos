"""
Sheets: añadir fila con columnas A=Asunto, B=Correo Pagador, C=Fecha Pago, D=Cédula, E=Monto, F=Referencia, G=Link.
"""
import logging
from typing import Any, List

logger = logging.getLogger(__name__)


def append_row(service_sheets: Any, spreadsheet_id: str, row: List[Any]) -> bool:
    """Añade una fila al sheet (hoja 0).
    row = [asunto, correo_pagador, fecha_pago, cedula, monto, referencia, link]
    La columna B (correo_pagador) contiene el email del remitente original del Fwd: para trazabilidad.
    """
    try:
        body = {"values": [row]}
        service_sheets.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="A:G",  # Sin nombre de hoja: usa la primera (compatible con cualquier locale)
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        return True
    except Exception as e:
        logger.exception("Sheets append_row: %s", e)
        return False
