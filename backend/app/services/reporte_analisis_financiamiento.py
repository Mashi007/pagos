"""
Excel "Análisis financiamiento": misma lógica que Fecha Drive (cruce por cédula) pero compara
total financiamiento en la hoja sincronizada vs préstamos en BD.
Columnas: ID préstamo | Cédula Drive | Cédula Sistema | Total financiamiento Drive | Total financiamiento sistema.
Ausencia en un lado: NE.
"""
from __future__ import annotations

import io
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.conciliacion_sheet import ConciliacionSheetMeta, ConciliacionSheetRow
from app.models.prestamo import Prestamo
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento

logger = logging.getLogger(__name__)

NE = "NE"


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


def _pick_total_financiamiento_header(headers: List[str]) -> Optional[str]:
    """Cabecera de la hoja para monto total (ej. TOTAL FINANCIAMIENTO)."""
    for h in headers:
        hl = re.sub(r"\s+", " ", (h or "").strip().casefold())
        if "total" in hl and "financiam" in hl:
            return h
    for h in headers:
        hl = (h or "").strip().casefold()
        if hl == "monto" or "financiamiento" in hl:
            return h
    return None


def _fmt_sistema_monto(v: Any) -> str:
    if v is None:
        return NE
    try:
        d = Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError):
        return NE
    if d == 0 and str(v).strip() == "":
        return NE
    return f"{d.quantize(Decimal('0.01')):.2f}"


def _parse_drive_monto_display(raw: str) -> str:
    """Normaliza texto de celda (864, 0,00, 1.440,50) a string numérico con 2 decimales o NE."""
    s = _as_text(raw)
    if not s:
        return NE
    t = s.replace(" ", "")
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        v = float(t)
        return f"{v:.2f}"
    except ValueError:
        return s if s else NE


def _latest_prestamo_por_cedula_norm(
    db: Session,
) -> Dict[str, Tuple[int, str, Any]]:
    rows = db.execute(
        select(Prestamo.cedula, Prestamo.id, Prestamo.total_financiamiento).order_by(Prestamo.id)
    ).all()
    out: Dict[str, Tuple[int, str, Any]] = {}
    for cedula, pid, tf in rows:
        c = (cedula or "").strip()
        if not c:
            continue
        nk = _norm_cedula_lookup(c)
        if nk:
            out[nk] = (int(pid), c, tf)
    return out


def build_analisis_financiamiento_excel(db: Session) -> Tuple[bytes, int]:
    """
    Una fila por fila de la hoja (orden por cédula Drive) + préstamos en BD sin cédula en la hoja.
    """
    import openpyxl

    logger.info("[analisis_financiamiento] build_analisis_financiamiento_excel inicio")

    meta = db.get(ConciliacionSheetMeta, 1)
    headers = list(meta.headers) if meta and meta.headers else []
    if not headers:
        logger.warning("[analisis_financiamiento] abort: sin cabeceras en conciliacion_sheet_meta")
        raise ValueError(
            "No hay cabeceras de la hoja sincronizada. Sincronice desde Drive: "
            "POST /api/v1/conciliacion-sheet/sync-now (sesión staff) o POST /api/v1/conciliacion-sheet/sync (cron con secreto)."
        )

    cedula_key = _pick_cedula_header(headers)
    if not cedula_key:
        logger.warning(
            "[analisis_financiamiento] abort: no se detectó columna cédula entre cabeceras=%r",
            headers[:12],
        )
        raise ValueError("No se pudo determinar la columna de cédula en la hoja.")

    monto_key = _pick_total_financiamiento_header(headers)
    if not monto_key:
        logger.warning(
            "[analisis_financiamiento] abort: no se detectó columna total financiamiento entre cabeceras=%r",
            headers[:12],
        )
        raise ValueError(
            "No se pudo determinar la columna de total financiamiento en la hoja "
            "(busque un título que contenga 'total' y 'financiam')."
        )

    logger.info(
        "[analisis_financiamiento] columnas clave: cedula_key=%r monto_key=%r n_headers=%s",
        cedula_key,
        monto_key,
        len(headers),
    )

    sheet_rows = db.execute(
        select(ConciliacionSheetRow).order_by(ConciliacionSheetRow.row_index)
    ).scalars().all()
    if not sheet_rows:
        logger.warning("[analisis_financiamiento] abort: conciliacion_sheet_rows vacío")
        raise ValueError(
            "No hay filas en conciliacion_sheet_rows. Ejecute sincronización desde Drive "
            "(POST /api/v1/conciliacion-sheet/sync-now o sync con secreto)."
        )

    latest = _latest_prestamo_por_cedula_norm(db)
    logger.info(
        "[analisis_financiamiento] préstamos indexados por cédula normalizada: %s",
        len(latest),
    )

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
    ws.title = "Análisis financiamiento"
    ws.append(
        [
            "ID prestamo",
            "Cédula Drive",
            "Cédula Sistema",
            "Total financiamiento Drive",
            "Total financiamiento sistema",
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

        val_monto_raw = _as_text(cells.get(monto_key))
        col_d = _parse_drive_monto_display(val_monto_raw) if val_monto_raw else NE

        if matched:
            pid, cedula_bd, tf = latest[nk]
            col_a = str(pid)
            col_c = (cedula_bd or "").strip() or NE
            col_e = _fmt_sistema_monto(tf)
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
        col_e = _fmt_sistema_monto(getattr(p, "total_financiamiento", None))
        ws.append([col_a, col_b, col_c, col_d, col_e])

    n = len(pending) + solo_count
    buf = io.BytesIO()
    wb.save(buf)
    out_bytes = buf.getvalue()
    logger.info(
        "[analisis_financiamiento] OK filas_excel=%s (hoja=%s solo_sistema=%s) bytes=%s",
        n,
        len(pending),
        solo_count,
        len(out_bytes),
    )
    return out_bytes, n
