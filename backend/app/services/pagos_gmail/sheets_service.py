"""
Sheets: añadir fila con columnas:
  A = Correo Pagador  (email extraído del Fwd: o remitente directo)
  B = Fecha Pago      (extraída de la imagen/adjunto por Gemini)
  C = Cédula          (extraída de la imagen/adjunto por Gemini)
  D = Monto           (extraído de la imagen/adjunto por Gemini)
  E = Referencia      (serial / nº documento / código transferencia — imagen/adjunto)
  F = Link            (enlace Google Drive al archivo adjunto)
"""
import logging
from typing import Any, List

logger = logging.getLogger(__name__)


def append_row(service_sheets: Any, spreadsheet_id: str, row: List[Any]) -> bool:
    """Añade una fila al sheet (hoja 0).
    row = [correo_pagador, fecha_pago, cedula, monto, referencia, link]
    """
    try:
        body = {"values": [row]}
        service_sheets.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="A:F",  # Sin nombre de hoja: usa la primera (compatible con cualquier locale)
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()
        return True
    except Exception as e:
        logger.exception("Sheets append_row: %s", e)
        return False
