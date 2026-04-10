"""
Sincroniza la pestaña CONCILIACIÓN de un Google Spreadsheet hacia PostgreSQL (último snapshot).
Solo lee el rango de columnas configurado (por defecto A:S); el resto de la hoja se ignora.
Credenciales: get_google_credentials (OAuth / cuenta de servicio desde Informe de pagos) o pipeline Gmail.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import BUSINESS_TIMEZONE
from app.models.conciliacion_sheet import (
    ConciliacionSheetMeta,
    ConciliacionSheetRow,
    ConciliacionSheetSyncRun,
)

logger = logging.getLogger(__name__)

SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
# Tokens existentes suelen traer scope spreadsheets completo; si readonly falla, reintentar.
SCOPES_SHEETS_FALLBACK = ["https://www.googleapis.com/auth/spreadsheets"]

MAX_SCAN_ROWS_FOR_HEADER = 80


def _col_letter_to_index1(col: str) -> int:
    """Índice 1-based de columna tipo Excel (A=1, Z=26, AA=27)."""
    n = 0
    for c in (col or "").strip().upper():
        if "A" <= c <= "Z":
            n = n * 26 + (ord(c) - ord("A") + 1)
    return max(n, 1)


def _parse_columns_range(spec: str) -> Tuple[str, str, int]:
    """
    Valida y parsea ej. 'A:S' -> (start_letter, end_letter, num_columns).
    Por defecto A:S si el formato es inválido.
    """
    raw = (spec or "A:S").strip().upper().replace(" ", "")
    if ":" not in raw:
        return "A", "S", 19
    left, right = raw.split(":", 1)
    left = left.strip().upper() or "A"
    right = right.strip().upper() or "S"
    if not left.isalpha() or not right.isalpha():
        return "A", "S", 19
    i1, i2 = _col_letter_to_index1(left), _col_letter_to_index1(right)
    if i2 < i1:
        left, right, i1, i2 = right, left, i2, i1
    ncols = i2 - i1 + 1
    if ncols > 200:
        raise ValueError("CONCILIACION_SHEET_COLUMNS_RANGE excede el máximo permitido (200 columnas).")
    return left, right, ncols


def _trim_row_width(row: List[Any], width: int) -> List[Any]:
    r = list(row or [])
    if len(r) > width:
        return r[:width]
    return r


def _cell_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    return str(v).strip()


def _titles_match(found: str, expected: str) -> bool:
    return (found or "").strip().casefold() == (expected or "").strip().casefold()


def _escape_sheet_title_for_range(title: str) -> str:
    return (title or "").replace("'", "''")


def _find_header_row(values: List[List[Any]], marker: str) -> int:
    """Índice 0-based de la fila cuya primera columna coincide con marker (casefold)."""
    want = (marker or "LOTE").strip().casefold()
    limit = min(len(values), MAX_SCAN_ROWS_FOR_HEADER)
    for i in range(limit):
        row = values[i] if i < len(values) else []
        if not row:
            continue
        if _cell_str(row[0]).casefold() == want:
            return i
    return 0


def _build_headers(raw_header: List[Any]) -> List[str]:
    seen: Dict[str, int] = {}
    out: List[str] = []
    for idx, cell in enumerate(raw_header):
        base = _cell_str(cell) or f"_col_{idx + 1}"
        n = seen.get(base, 0)
        if n:
            key = f"{base} ({n + 1})"
            seen[base] = n + 1
        else:
            key = base
            seen[base] = 1
        out.append(key)
    return out


def _row_to_cells(headers: List[str], row: List[Any]) -> Dict[str, Any]:
    d: Dict[str, Any] = {}
    for i, h in enumerate(headers):
        val = row[i] if i < len(row) else None
        if val is None or (isinstance(val, str) and val.strip() == ""):
            d[h] = None
        else:
            d[h] = val
    return d


def _resolve_sheet_title(service: Any, spreadsheet_id: str, expected_tab: str) -> str:
    meta = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets(properties(title,sheetId))")
        .execute()
    )
    sheets = meta.get("sheets") or []
    for s in sheets:
        title = (s.get("properties") or {}).get("title") or ""
        if _titles_match(title, expected_tab):
            return title
    titles = [(s.get("properties") or {}).get("title") for s in sheets]
    raise ValueError(
        f"No se encontró la pestaña {expected_tab!r}. Pestañas disponibles: {titles!r}"
    )


def _get_sheets_credentials():
    """OAuth/SA con lectura Sheets; fallback a credenciales Gmail pipeline."""
    from app.core.google_credentials import get_google_credentials

    creds = get_google_credentials(SCOPES_SHEETS)
    if creds is not None:
        return creds
    creds = get_google_credentials(SCOPES_SHEETS_FALLBACK)
    if creds is not None:
        return creds
    try:
        from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials

        return get_pagos_gmail_credentials()
    except Exception:
        return None


def fetch_sheet_values(
    spreadsheet_id: str, tab_name: str, columns_range: str
) -> Tuple[str, List[List[Any]], int]:
    creds = _get_sheets_credentials()
    if creds is None:
        raise RuntimeError(
            "Sin credenciales Google (Sheets). Configure Informe de pagos / cuenta de servicio "
            "o tokens Gmail (GOOGLE_CLIENT_ID, GMAIL_TOKENS_PATH, etc.)."
        )
    from googleapiclient.discovery import build

    col_a, col_b, ncols = _parse_columns_range(columns_range)
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    exact_title = _resolve_sheet_title(service, spreadsheet_id, tab_name)
    rng = f"'{_escape_sheet_title_for_range(exact_title)}'!{col_a}:{col_b}"
    resp = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=rng,
            majorDimension="ROWS",
            valueRenderOption="FORMATTED_VALUE",
        )
        .execute()
    )
    values = resp.get("values") or []
    trimmed = [_trim_row_width(row, ncols) for row in values]
    return exact_title, trimmed, ncols


def run_sync_to_db(db: Session) -> Dict[str, Any]:
    """
    Descarga la pestaña configurada y reemplaza conciliacion_sheet_rows.
    Registra conciliacion_sheet_sync_run (una fila por ejecución).
    """
    spreadsheet_id = (getattr(settings, "CONCILIACION_SHEET_SPREADSHEET_ID", None) or "").strip()
    if not spreadsheet_id:
        raise ValueError("CONCILIACION_SHEET_SPREADSHEET_ID no está configurado.")

    tab_name = (getattr(settings, "CONCILIACION_SHEET_TAB_NAME", None) or "CONCILIACIÓN").strip()
    marker = (getattr(settings, "CONCILIACION_SHEET_HEADER_MARKER", None) or "LOTE").strip()
    columns_range = (getattr(settings, "CONCILIACION_SHEET_COLUMNS_RANGE", None) or "A:S").strip()

    t0 = time.perf_counter()
    started = datetime.now(timezone.utc)

    try:
        sheet_title, values, ncols_expected = fetch_sheet_values(
            spreadsheet_id, tab_name, columns_range
        )
        if not values:
            raise ValueError("La hoja devolvió 0 filas.")

        h_idx = _find_header_row(values, marker)
        raw_header = _trim_row_width(values[h_idx], ncols_expected)
        headers = _build_headers(raw_header)
        col_count = len(headers)

        data_rows = values[h_idx + 1 :]
        while data_rows and all(_cell_str(c) == "" for c in (data_rows[-1] or [])):
            data_rows.pop()

        now = datetime.now(timezone.utc)
        meta = db.get(ConciliacionSheetMeta, 1)
        if meta is None:
            meta = ConciliacionSheetMeta(id=1)
            db.add(meta)

        db.execute(delete(ConciliacionSheetRow))
        batch: List[ConciliacionSheetRow] = []
        for offset, row in enumerate(data_rows):
            sheet_row_number = h_idx + 2 + offset
            cells = _row_to_cells(headers, _trim_row_width(row or [], ncols_expected))
            batch.append(ConciliacionSheetRow(row_index=sheet_row_number, cells=cells))
            if len(batch) >= 400:
                db.add_all(batch)
                db.flush()
                batch.clear()
        if batch:
            db.add_all(batch)

        meta.spreadsheet_id = spreadsheet_id
        meta.sheet_title = sheet_title
        meta.headers = headers
        meta.header_row_index = h_idx + 1
        meta.row_count = len(data_rows)
        meta.col_count = col_count
        meta.synced_at = now
        meta.last_error = None
        meta.updated_at = now

        run = ConciliacionSheetSyncRun(
            started_at=started,
            finished_at=now,
            success=True,
            message="OK",
            row_count=len(data_rows),
            col_count=col_count,
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return {
            "ok": True,
            "sheet_title": sheet_title,
            "columns_range": columns_range,
            "header_row_index": h_idx + 1,
            "row_count": len(data_rows),
            "col_count": col_count,
            "synced_at": now.isoformat(),
            "timezone": BUSINESS_TIMEZONE,
            "run_id": run.id,
        }
    except Exception as e:
        logger.exception("conciliacion_sheet sync: %s", e)
        db.rollback()
        finished = datetime.now(timezone.utc)
        run = ConciliacionSheetSyncRun(
            started_at=started,
            finished_at=finished,
            success=False,
            message=str(e)[:2000],
            row_count=0,
            col_count=0,
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
        db.add(run)
        meta = db.get(ConciliacionSheetMeta, 1)
        if meta is None:
            meta = ConciliacionSheetMeta(id=1)
            db.add(meta)
        meta.spreadsheet_id = spreadsheet_id or meta.spreadsheet_id or ""
        meta.sheet_title = tab_name
        meta.last_error = str(e)[:4000]
        meta.updated_at = finished
        try:
            db.commit()
        except Exception:
            db.rollback()
        raise
