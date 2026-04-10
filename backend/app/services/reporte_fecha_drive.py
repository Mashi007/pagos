"""
Excel "Fecha Drive": compara hoja Drive (sync) vs préstamos en BD.
Columnas: ID préstamo | Cédula Drive | Cédula Sistema | Fecha aprobación Drive (Q) | Fecha aprobación sistema.
Valor ausente en un lado: NE (como el ejemplo operativo).
"""
from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conciliacion_sheet import ConciliacionSheetMeta, ConciliacionSheetRow
from app.models.prestamo import Prestamo
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento

COL_SHEET_Q_INDEX = 16

NE = "NE"

# Meses abreviados en hoja tipo "14-oct-24"
_MESES = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}


def _fmt_sistema_dt(v: Optional[datetime]) -> str:
    if v is None:
        return NE
    if hasattr(v, "isoformat"):
        s = v.isoformat(sep=" ", timespec="seconds")
        return s if s.strip() else NE
    return str(v) if str(v).strip() else NE


def _as_text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    return str(v).strip()


def _norm_cedula_lookup(raw: str) -> str:
    n = normalizar_cedula_almacenamiento(raw)
    return (n or "").strip().upper()


def _pick_cedula_header(headers: List[str]) -> Optional[str]:
    for h in headers:
        hl = (h or "").strip().casefold()
        if "cedula identidad" in hl or hl == "cedula" or hl == "cédula":
            return h
    for h in headers:
        hl = (h or "").strip().casefold()
        if "cedula" in hl or "cédula" in hl:
            return h
    if len(headers) > 4:
        return headers[4]
    return headers[0] if headers else None


def _parse_drive_date(raw: str) -> str:
    """
    Normaliza fecha de la columna Q a YYYY-MM-DD. Si no se reconoce, devuelve el texto no vacío o NE.
    """
    s = _as_text(raw)
    if not s:
        return NE

    # YYYY-MM-DD o inicio ISO
    if len(s) >= 10 and s[4] == "-" and s[7] == "-" and s[:10].replace("-", "").isdigit():
        return s[:10]

    # DD/MM/YYYY o D/M/YYYY
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}"

    # DD-mon-YY o D-mon-YY (ej. 14-oct-24)
    m2 = re.match(
        r"^(\d{1,2})-([a-zA-Z]{3,})-(\d{2,4})$",
        s.replace(" ", ""),
    )
    if m2:
        d = int(m2.group(1))
        mon = m2.group(2).lower()[:3]
        yr = int(m2.group(3))
        if yr < 100:
            yr += 2000 if yr < 50 else 1900
        mo = _MESES.get(mon)
        if mo and 1 <= d <= 31:
            return f"{yr:04d}-{mo:02d}-{d:02d}"

    return s


def _latest_prestamo_por_cedula_norm(
    db: Session,
) -> Dict[str, Tuple[int, str, Optional[datetime]]]:
    rows = db.execute(
        select(Prestamo.cedula, Prestamo.id, Prestamo.fecha_aprobacion).order_by(Prestamo.id)
    ).all()
    out: Dict[str, Tuple[int, str, Optional[datetime]]] = {}
    for cedula, pid, fap in rows:
        c = (cedula or "").strip()
        if not c:
            continue
        nk = _norm_cedula_lookup(c)
        if nk:
            out[nk] = (int(pid), c, fap)
    return out


def build_fecha_drive_excel(db: Session) -> Tuple[bytes, int]:
    """
    Filas (1) una por fila Drive ordenadas por cédula Drive; (2) préstamos en BD sin cédula en Drive.
    """
    import openpyxl

    meta = db.get(ConciliacionSheetMeta, 1)
    headers = list(meta.headers) if meta and meta.headers else []
    if not headers:
        raise ValueError(
            "No hay cabeceras de la hoja sincronizada. Ejecute POST /conciliacion-sheet/sync primero."
        )
    if len(headers) <= COL_SHEET_Q_INDEX:
        raise ValueError(
            "La hoja sincronizada no incluye la columna Q (se requiere rango hasta S). "
            "Verifique CONCILIACION_SHEET_COLUMNS_RANGE y vuelva a sincronizar."
        )

    cedula_key = _pick_cedula_header(headers)
    if not cedula_key:
        raise ValueError("No se pudo determinar la columna de cédula en la hoja.")

    key_q = headers[COL_SHEET_Q_INDEX]

    sheet_rows = db.execute(
        select(ConciliacionSheetRow).order_by(ConciliacionSheetRow.row_index)
    ).scalars().all()
    if not sheet_rows:
        raise ValueError(
            "No hay filas en conciliacion_sheet_rows. Sincronice la hoja CONCILIACIÓN primero."
        )

    latest = _latest_prestamo_por_cedula_norm(db)

    drive_norm_cedulas: set[str] = set()
    for sr in sheet_rows:
        cells = sr.cells or {}
        if not isinstance(cells, dict):
            continue
        raw = _as_text(cells.get(cedula_key))
        nk = _norm_cedula_lookup(raw)
        if nk:
            drive_norm_cedulas.add(nk)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Fecha Drive"
    ws.append(
        [
            "ID prestamo",
            "Cédula Drive",
            "Cédula Sistema",
            "Fecha Aprobacion Drive",
            "Fecha de aprobación Sistema",
        ]
    )

    pending: List[Tuple[Tuple[int, str, int], List[str]]] = []

    for sr in sheet_rows:
        cells = sr.cells or {}
        if not isinstance(cells, dict):
            continue

        cedula_drive_raw = _as_text(cells.get(cedula_key))
        col_b = cedula_drive_raw if cedula_drive_raw else NE

        nk = _norm_cedula_lookup(cedula_drive_raw)
        matched = bool(nk) and nk in latest

        val_q_raw = _as_text(cells.get(key_q))
        col_d = _parse_drive_date(val_q_raw) if val_q_raw else NE

        if matched:
            pid, cedula_bd, fap = latest[nk]
            col_a = str(pid)
            col_c = (cedula_bd or "").strip() or NE
            col_e = _fmt_sistema_dt(fap)
        else:
            col_a = NE
            col_c = NE
            col_e = NE

        sort_pri = 0 if nk else 1
        sort_key = nk if nk else ""
        pending.append(
            (
                (sort_pri, sort_key, int(sr.row_index)),
                [col_a, col_b, col_c, col_d, col_e],
            )
        )

    pending.sort(key=lambda x: x[0])

    for _sk, row_vals in pending:
        ws.append(row_vals)

    solo_sistema = db.execute(select(Prestamo).order_by(Prestamo.id)).scalars().all()
    solo_count = 0
    for p in solo_sistema:
        nk = _norm_cedula_lookup(p.cedula or "")
        if not nk or nk in drive_norm_cedulas:
            continue
        solo_count += 1
        col_d = NE
        col_b = NE
        col_a = str(p.id)
        col_c = (p.cedula or "").strip() or NE
        col_e = _fmt_sistema_dt(getattr(p, "fecha_aprobacion", None))
        ws.append([col_a, col_b, col_c, col_d, col_e])

    n = len(pending) + solo_count
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue(), n
