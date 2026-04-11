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

from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import BUSINESS_TIMEZONE
from app.models.conciliacion_sheet import (
    ConciliacionSheetMeta,
    ConciliacionSheetRow,
    ConciliacionSheetSyncRun,
)
from app.models.drive import DRIVE_COL_COUNT, DRIVE_COLUMN_NAMES, DriveRow

logger = logging.getLogger(__name__)

SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
# Tokens existentes suelen traer scope spreadsheets completo; si readonly falla, reintentar.
SCOPES_SHEETS_FALLBACK = ["https://www.googleapis.com/auth/spreadsheets"]

MAX_SCAN_ROWS_FOR_HEADER = 80


def _mask_spreadsheet_id(spreadsheet_id: str) -> str:
    """Evita volcar el ID completo en logs; basta para correlacionar en soporte."""
    s = (spreadsheet_id or "").strip()
    if not s:
        return "(vacío)"
    if len(s) <= 10:
        return f"{s[:3]}…(len={len(s)})"
    return f"{s[:4]}…{s[-4:]}(len={len(s)})"


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


def _drive_kwargs_from_row(row: List[Any], source_ncols: int) -> Dict[str, Any]:
    """Primeras A..S (19) celdas de la fila de la hoja como col_a..col_s (TEXT o NULL)."""
    trimmed = _trim_row_width(row or [], min(int(source_ncols or 0), DRIVE_COL_COUNT))
    out: Dict[str, Any] = {}
    for i, colname in enumerate(DRIVE_COLUMN_NAMES):
        if i < len(trimmed):
            s = _cell_str(trimmed[i])
            out[colname] = s if s else None
        else:
            out[colname] = None
    return out


def _titles_match(found: str, expected: str) -> bool:
    return (found or "").strip().casefold() == (expected or "").strip().casefold()


def _escape_sheet_title_for_range(title: str) -> str:
    return (title or "").replace("'", "''")


def _find_header_row(values: List[List[Any]], marker: str) -> Tuple[int, bool]:
    """
    Índice 0-based de la fila cuya primera columna coincide con marker (casefold).
    Devuelve (índice, True) si hubo coincidencia; si no, (0, False) y se asume fila 0 como cabecera
    (registrar advertencia en el caller).
    """
    want = (marker or "LOTE").strip().casefold()
    limit = min(len(values), MAX_SCAN_ROWS_FOR_HEADER)
    for i in range(limit):
        row = values[i] if i < len(values) else []
        if not row:
            continue
        if _cell_str(row[0]).casefold() == want:
            return i, True
    return 0, False


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
    logger.warning(
        "[conciliacion_sheet] pestaña no encontrada: buscada=%r disponibles=%r spreadsheet=%s",
        expected_tab,
        titles,
        _mask_spreadsheet_id(spreadsheet_id),
    )
    raise ValueError(
        f"No se encontró la pestaña {expected_tab!r}. Pestañas disponibles: {titles!r}"
    )


def _get_sheets_credentials():
    """OAuth/SA con lectura Sheets; fallback a credenciales Gmail pipeline."""
    from app.core.google_credentials import get_google_credentials

    creds = get_google_credentials(SCOPES_SHEETS)
    if creds is not None:
        logger.info(
            "[conciliacion_sheet] credenciales Google: ruta principal (spreadsheets.readonly)"
        )
        return creds
    creds = get_google_credentials(SCOPES_SHEETS_FALLBACK)
    if creds is not None:
        logger.info(
            "[conciliacion_sheet] credenciales Google: alcance spreadsheets (fallback)"
        )
        return creds
    try:
        from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials

        creds = get_pagos_gmail_credentials()
        if creds is not None:
            logger.info("[conciliacion_sheet] credenciales Google: fallback pagos_gmail")
        return creds
    except Exception as ex:
        logger.warning(
            "[conciliacion_sheet] credenciales Gmail no disponibles: %s",
            type(ex).__name__,
        )
        return None


def fetch_sheet_values(
    spreadsheet_id: str, tab_name: str, columns_range: str
) -> Tuple[str, List[List[Any]], int]:
    logger.info(
        "[conciliacion_sheet] fetch_sheet_values inicio spreadsheet=%s tab_solicitada=%r cols=%r",
        _mask_spreadsheet_id(spreadsheet_id),
        tab_name,
        columns_range,
    )
    creds = _get_sheets_credentials()
    if creds is None:
        logger.error(
            "[conciliacion_sheet] fetch_sheet_values abortado: sin credenciales Google"
        )
        raise RuntimeError(
            "Sin credenciales Google (Sheets). Configure Informe de pagos / cuenta de servicio "
            "o tokens Gmail (GOOGLE_CLIENT_ID, GMAIL_TOKENS_PATH, etc.)."
        )
    from googleapiclient.discovery import build

    col_a, col_b, ncols = _parse_columns_range(columns_range)
    service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    exact_title = _resolve_sheet_title(service, spreadsheet_id, tab_name)
    rng = f"'{_escape_sheet_title_for_range(exact_title)}'!{col_a}:{col_b}"
    logger.info(
        "[conciliacion_sheet] Sheets API values.get rango=%r pestaña_resuelta=%r ncols=%s",
        rng,
        exact_title,
        ncols,
    )
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
    logger.info(
        "[conciliacion_sheet] fetch_sheet_values ok filas_brutas=%s filas_trim=%s",
        len(values),
        len(trimmed),
    )
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

    logger.info(
        "[conciliacion_sheet] run_sync_to_db inicio spreadsheet=%s tab=%r marker=%r cols=%r",
        _mask_spreadsheet_id(spreadsheet_id),
        tab_name,
        marker,
        columns_range,
    )

    try:
        sheet_title, values, ncols_expected = fetch_sheet_values(
            spreadsheet_id, tab_name, columns_range
        )
        if not values:
            logger.warning("[conciliacion_sheet] run_sync_to_db: API devolvió 0 filas")
            raise ValueError("La hoja devolvió 0 filas.")

        h_idx, marker_hit = _find_header_row(values, marker)
        if not marker_hit:
            logger.warning(
                "[conciliacion_sheet] No se encontró %r en columna A en las primeras %s filas; "
                "se usa la fila 1 (índice 0) como cabecera. Si las cabeceras quedan vacías o mal, "
                "defina CONCILIACION_SHEET_HEADER_MARKER con el texto exacto de la columna A de la fila de títulos.",
                marker,
                min(len(values), MAX_SCAN_ROWS_FOR_HEADER),
            )
        logger.info(
            "[conciliacion_sheet] cabecera: fila_marcador_idx_0based=%s marker_hit=%s (marker=%r) filas_totales=%s",
            h_idx,
            marker_hit,
            marker,
            len(values),
        )
        raw_header = _trim_row_width(values[h_idx], ncols_expected)
        headers = _build_headers(raw_header)
        col_count = len(headers)
        logger.info(
            "[conciliacion_sheet] cabeceras parseadas: n=%s primeras=%r",
            col_count,
            headers[:8],
        )
        if col_count == 0:
            raise ValueError(
                f"La fila de cabecera (fila {h_idx + 1} en la pestaña) no tiene celdas en el rango {columns_range!r}. "
                f"Confirme que la primera columna de la fila de títulos sea exactamente {marker!r} "
                "(o ajuste CONCILIACION_SHEET_HEADER_MARKER al valor de la columna A de esa fila) "
                f"en las primeras {min(len(values), MAX_SCAN_ROWS_FOR_HEADER)} filas, y que el rango incluya las columnas con texto."
            )

        data_rows = values[h_idx + 1 :]
        while data_rows and all(_cell_str(c) == "" for c in (data_rows[-1] or [])):
            data_rows.pop()
        logger.info(
            "[conciliacion_sheet] filas_datos_tras_trim_final=%s",
            len(data_rows),
        )

        now = datetime.now(timezone.utc)
        meta = db.get(ConciliacionSheetMeta, 1)
        if meta is None:
            meta = ConciliacionSheetMeta(id=1)
            db.add(meta)

        db.execute(delete(ConciliacionSheetRow))
        db.execute(delete(DriveRow))
        batch: List[ConciliacionSheetRow] = []
        batch_drive: List[DriveRow] = []
        for offset, row in enumerate(data_rows):
            sheet_row_number = h_idx + 2 + offset
            cells = _row_to_cells(headers, _trim_row_width(row or [], ncols_expected))
            batch.append(ConciliacionSheetRow(row_index=sheet_row_number, cells=cells))
            batch_drive.append(
                DriveRow(
                    sheet_row_number=sheet_row_number,
                    synced_at=now,
                    **_drive_kwargs_from_row(row, ncols_expected),
                )
            )
            if len(batch) >= 400:
                db.add_all(batch)
                db.add_all(batch_drive)
                db.flush()
                batch.clear()
                batch_drive.clear()
        if batch:
            db.add_all(batch)
        if batch_drive:
            db.add_all(batch_drive)

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
        logger.info(
            "[conciliacion_sheet] run_sync_to_db OK run_id=%s filas=%s cols=%s drive_filas=%s duracion_ms=%s",
            run.id,
            len(data_rows),
            col_count,
            len(data_rows),
            run.duration_ms,
        )
        return {
            "ok": True,
            "sheet_title": sheet_title,
            "columns_range": columns_range,
            "header_row_index": h_idx + 1,
            "row_count": len(data_rows),
            "col_count": col_count,
            "drive_rows": len(data_rows),
            "synced_at": now.isoformat(),
            "timezone": BUSINESS_TIMEZONE,
            "run_id": run.id,
        }
    except Exception as e:
        logger.exception(
            "[conciliacion_sheet] run_sync_to_db ERROR tras_ms=%s err=%s",
            int((time.perf_counter() - t0) * 1000),
            e,
        )
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


# Mínimo de columnas A..Q (índice 16) para el reporte Fecha Drive.
_MIN_HEADERS_FECHA_DRIVE = 17


def ping_google_spreadsheet_metadata(spreadsheet_id: str) -> Dict[str, Any]:
    """
    Una sola llamada a la API de Sheets (metadatos del libro). No lee celdas.
    Sirve para verificar ID + credenciales sin ejecutar sync completo.
    """
    sid = (spreadsheet_id or "").strip()
    if not sid:
        return {"ok": False, "step": "no_spreadsheet_id"}

    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    try:
        creds = _get_sheets_credentials()
        if creds is None:
            return {"ok": False, "step": "no_credentials"}

        service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        meta = (
            service.spreadsheets()
            .get(spreadsheetId=sid, fields="properties(title,locale,timeZone)")
            .execute()
        )
        props = meta.get("properties") or {}
        logger.info(
            "[conciliacion_sheet] ping_google ok spreadsheet=%s title=%r",
            _mask_spreadsheet_id(sid),
            props.get("title"),
        )
        return {
            "ok": True,
            "step": "metadata_ok",
            "spreadsheet_title": props.get("title"),
            "locale": props.get("locale"),
            "time_zone": props.get("timeZone"),
        }
    except HttpError as e:
        st = getattr(getattr(e, "resp", None), "status", None)
        logger.warning(
            "[conciliacion_sheet] ping_google HttpError status=%s spreadsheet=%s",
            st,
            _mask_spreadsheet_id(sid),
        )
        return {
            "ok": False,
            "step": "google_http_error",
            "status": st,
            "message": str(e)[:400],
        }
    except Exception as e:
        logger.warning(
            "[conciliacion_sheet] ping_google error spreadsheet=%s err=%s",
            _mask_spreadsheet_id(sid),
            type(e).__name__,
        )
        return {
            "ok": False,
            "step": "exception",
            "error_type": type(e).__name__,
            "message": str(e)[:400],
        }


def build_conciliacion_sheet_diagnostico(db: Session) -> Dict[str, Any]:
    """
    Resumen agregado para soporte: variables de entorno, filas en BD y ping a Google.
    No modifica datos.
    """
    checks: List[Dict[str, Any]] = []
    next_steps: List[str] = []

    sid = (getattr(settings, "CONCILIACION_SHEET_SPREADSHEET_ID", None) or "").strip()
    tab_cfg = (getattr(settings, "CONCILIACION_SHEET_TAB_NAME", None) or "CONCILIACIÓN").strip()
    cols_cfg = (getattr(settings, "CONCILIACION_SHEET_COLUMNS_RANGE", None) or "A:S").strip()

    ok_id = bool(sid)
    checks.append(
        {
            "id": "env_CONCILIACION_SHEET_SPREADSHEET_ID",
            "ok": ok_id,
            "detail": _mask_spreadsheet_id(sid) if sid else "no configurado",
        }
    )
    if not ok_id:
        next_steps.append("Defina CONCILIACION_SHEET_SPREADSHEET_ID en el backend (.env / Render).")

    meta = db.get(ConciliacionSheetMeta, 1)
    checks.append(
        {
            "id": "db_conciliacion_sheet_meta",
            "ok": meta is not None,
            "detail": "fila id=1 presente" if meta else "sin meta (nunca hubo sync exitoso)",
        }
    )

    hdrs: List[str] = list(meta.headers) if meta and meta.headers else []
    ok_hdr = len(hdrs) >= _MIN_HEADERS_FECHA_DRIVE
    checks.append(
        {
            "id": "headers_reach_column_Q",
            "ok": ok_hdr,
            "detail": f"cabeceras={len(hdrs)} (minimo {_MIN_HEADERS_FECHA_DRIVE} para columna Q)",
        }
    )
    if meta and hdrs and not ok_hdr:
        next_steps.append(
            f"Aumente CONCILIACION_SHEET_COLUMNS_RANGE (ahora {cols_cfg!r}) para incluir hasta la columna Q."
        )

    n_rows = int(
        db.execute(select(func.count()).select_from(ConciliacionSheetRow)).scalar_one() or 0
    )
    ok_rows = n_rows > 0
    checks.append(
        {
            "id": "db_conciliacion_sheet_rows",
            "ok": ok_rows,
            "detail": f"filas={n_rows}",
        }
    )
    if not ok_rows:
        next_steps.append(
            "Ejecute POST /api/v1/conciliacion-sheet/sync-now (sesión) o /sync (cron) tras configurar credenciales."
        )

    n_drive = int(db.execute(select(func.count()).select_from(DriveRow)).scalar_one() or 0)
    ok_drive = n_drive == n_rows
    checks.append(
        {
            "id": "db_drive_rows",
            "ok": ok_drive,
            "detail": f"filas_tabla_drive={n_drive} (columnas A..S; debe igualar filas snapshot={n_rows})",
        }
    )
    if n_rows > 0 and not ok_drive:
        next_steps.append(
            "La tabla drive no coincide con conciliacion_sheet_rows; ejecute sync-now o revise errores en la última corrida."
        )

    last_run = db.execute(
        select(ConciliacionSheetSyncRun).order_by(desc(ConciliacionSheetSyncRun.id)).limit(1)
    ).scalars().first()
    checks.append(
        {
            "id": "last_sync_run",
            "ok": last_run is not None and bool(last_run.success),
            "detail": None
            if last_run is None
            else {
                "id": last_run.id,
                "success": last_run.success,
                "message": (last_run.message or "")[:200],
                "row_count": last_run.row_count,
            },
        }
    )

    google_ping: Dict[str, Any] = {"skipped": True, "reason": "sin spreadsheet_id"}
    if sid:
        google_ping = ping_google_spreadsheet_metadata(sid)
        if not google_ping.get("ok"):
            next_steps.append(
                "Revise credenciales Google (Informe de pagos / Gmail) y que la cuenta tenga acceso al documento."
            )

    fecha_drive_ready = ok_id and ok_hdr and ok_rows and bool(meta) and bool(hdrs)
    if sid and not google_ping.get("ok"):
        fecha_drive_ready = False

    return {
        "component": "conciliacion_sheet",
        "settings": {
            "tab_name": tab_cfg,
            "columns_range": cols_cfg,
            "header_marker": (getattr(settings, "CONCILIACION_SHEET_HEADER_MARKER", None) or "LOTE").strip(),
            "sync_secret_configured": bool(
                (getattr(settings, "CONCILIACION_SHEET_SYNC_SECRET", None) or "").strip()
            ),
        },
        "checks": checks,
        "google_ping": google_ping,
        "meta_snapshot": None
        if meta is None
        else {
            "sheet_title": meta.sheet_title,
            "header_row_index": meta.header_row_index,
            "row_count_meta": meta.row_count,
            "col_count": meta.col_count,
            "synced_at": meta.synced_at.isoformat() if meta.synced_at else None,
            "last_error_preview": (meta.last_error or "")[:300] if meta.last_error else None,
        },
        "fecha_drive_ready": fecha_drive_ready,
        "next_steps": next_steps,
    }
