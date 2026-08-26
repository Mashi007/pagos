"""
Rellena columnas Email y Teléfono en hoja Drive de mora por cédula (clientes BD).

Hoja esperada (CSV export):
  A Cédula | B Estado | C Cuotas en mora | D Saldo vencido
  → escribe E Email | F Teléfono
"""
from __future__ import annotations

import csv
import io
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.services.reporte_cedulas_cuota_hoja import (
    _contacto_bd_por_cedula_norm,
    _contacto_para_cedula_hoja,
    parsear_cedulas_csv,
)

logger = logging.getLogger(__name__)

_SHEET_EXPORT = (
    "https://docs.google.com/spreadsheets/d/{sid}/export?format=csv"
)
DEFAULT_SHEET_ID = "1WSmDc5qP_l3FUFUx7oTlX5newCdTtZvJFy1Z4U5rHBw"


def _descargar_csv_hoja(spreadsheet_id: str) -> bytes:
    url = _SHEET_EXPORT.format(sid=spreadsheet_id.strip())
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "pagos-hoja-mora-contacto/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.read()
    except urllib.error.URLError as e:
        raise RuntimeError(f"No se pudo leer la hoja Drive: {e}") from e


def leer_filas_hoja_mora(spreadsheet_id: str) -> Tuple[List[List[str]], List[str]]:
    """
    Devuelve (filas_csv_completas, cédulas_datos).
    filas_csv[0] es encabezado; cédulas_datos alinea 1:1 con filas de datos (índice i>=1).
    """
    raw = _descargar_csv_hoja(spreadsheet_id)
    text = raw.decode("utf-8-sig", errors="replace")
    filas = list(csv.reader(io.StringIO(text)))
    if not filas:
        return [], []
    cedulas: List[str] = []
    for i, row in enumerate(filas):
        if i == 0:
            continue
        if not row:
            cedulas.append("")
            continue
        cedulas.append(str(row[0] or "").strip())
    return filas, cedulas


def contacto_para_filas_hoja(
    db: Session, cedulas: Sequence[str]
) -> List[Tuple[Optional[str], Optional[str]]]:
    """Un (email, teléfono) por fila de datos, en el mismo orden."""
    activas = [c for c in cedulas if c]
    mapa = _contacto_bd_por_cedula_norm(db, activas)
    out: List[Tuple[Optional[str], Optional[str]]] = []
    for ced in cedulas:
        if not ced:
            out.append((None, None))
            continue
        out.append(_contacto_para_cedula_hoja(ced, mapa))
    return out


def _get_sheets_service():
    from app.core.google_credentials import get_google_credentials
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = get_google_credentials(scopes)
    if not creds:
        raise RuntimeError(
            "Sin credenciales Google Sheets (OAuth o cuenta de servicio en informe pagos)."
        )
    return build("sheets", "v4", credentials=creds)


def escribir_contacto_en_hoja(
    spreadsheet_id: str,
    contactos: Sequence[Tuple[Optional[str], Optional[str]]],
    *,
    tab_name: Optional[str] = None,
) -> None:
    """Escribe E1:F encabezado + E2:F datos (Email, Teléfono)."""
    if not contactos:
        raise RuntimeError("No hay filas de contacto para escribir.")
    prefix = f"'{tab_name}'!" if tab_name else ""
    service = _get_sheets_service()
    header_range = f"{prefix}E1:F1"
    data_range = f"{prefix}E2:F{len(contactos) + 1}"
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id.strip(),
        range=header_range,
        valueInputOption="RAW",
        body={"values": [["Email", "Teléfono"]]},
    ).execute()
    values = [[em or "", tel or ""] for em, tel in contactos]
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id.strip(),
        range=data_range,
        valueInputOption="RAW",
        body={"values": values},
    ).execute()


def sincronizar_contacto_hoja_mora(
    db: Session,
    *,
    spreadsheet_id: str = DEFAULT_SHEET_ID,
    tab_name: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Lee cédulas de la hoja, busca email/teléfono en clientes y escribe columnas E–F.
    dry_run=True: solo estadísticas, no escribe en Drive.
    """
    _filas, cedulas = leer_filas_hoja_mora(spreadsheet_id)
    if not cedulas:
        raise RuntimeError("La hoja no tiene filas de datos.")
    contactos = contacto_para_filas_hoja(db, cedulas)
    con_email = sum(1 for em, _ in contactos if em)
    con_tel = sum(1 for _, tel in contactos if tel)
    con_ambos = sum(1 for em, tel in contactos if em and tel)
    sin_contacto = sum(
        1 for ced, (em, tel) in zip(cedulas, contactos) if ced and not em and not tel
    )
    stats = {
        "spreadsheet_id": spreadsheet_id,
        "filas_datos": len(cedulas),
        "cedulas_con_valor": sum(1 for c in cedulas if c),
        "con_email": con_email,
        "con_telefono": con_tel,
        "con_ambos": con_ambos,
        "sin_contacto": sin_contacto,
        "dry_run": dry_run,
        "escrito": False,
    }
    logger.info("[hoja_mora_contacto] stats=%s", stats)
    if dry_run:
        return stats
    escribir_contacto_en_hoja(spreadsheet_id, contactos, tab_name=tab_name)
    stats["escrito"] = True
    return stats


def generar_csv_contacto_hoja(
    db: Session,
    *,
    spreadsheet_id: str = DEFAULT_SHEET_ID,
) -> str:
    """CSV cédula,email,teléfono para pegar/importar en la hoja."""
    _filas, cedulas = leer_filas_hoja_mora(spreadsheet_id)
    contactos = contacto_para_filas_hoja(db, cedulas)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Cédula", "Email", "Teléfono"])
    for ced, (em, tel) in zip(cedulas, contactos):
        if not ced:
            continue
        w.writerow([ced, em or "", tel or ""])
    return buf.getvalue()
