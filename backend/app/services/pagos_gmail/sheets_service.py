"""
Sheets: añadir fila con columnas A=Asunto, B=Fecha Pago, C=Cédula, D=Monto, E=Referencia, F=Link.
"""
import logging
from typing import Any, List

logger = logging.getLogger(__name__)


def append_row(service_sheets: Any, spreadsheet_id: str, row: List[Any]) -> bool:
    """Añade una fila al sheet (hoja 0). row = [asunto, fecha_pago, cedula, monto, referencia, link]."""
    try:
        body = {"values": [row]}
        service_sheets.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="Sheet1!A:F",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        return True
    except Exception as e:
        logger.exception("Sheets append_row: %s", e)
        return False
