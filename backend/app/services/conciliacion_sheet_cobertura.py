"""
Cobertura del escaneo Drive (hoja CONCILIACIÓN): última fila con datos en BD vs cola en Google.

Usado por GET /conciliacion-sheet/status, POST /verificar-cola y tras cada sync exitoso.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.drive import DriveRow
from app.services.conciliacion_sheet_meta_access import (
    apply_scan_coverage_fields_to_meta,
    get_conciliacion_sheet_meta,
    meta_google_tail_row_number,
    meta_google_tail_row_probed_at_iso,
    meta_last_data_sheet_row_number,
)

logger = logging.getLogger(__name__)

# Ventana alrededor de la última fila conocida para no leer toda la hoja (~7k+ filas).
TAIL_PROBE_ROWS_ABOVE = 120
TAIL_PROBE_ROWS_BELOW = 60


def _cell_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    return str(v).strip()


def row_has_cell_data(row: List[Any] | None) -> bool:
    """True si alguna celda de la fila tiene contenido (cualquier columna del rango leído)."""
    if not row:
        return False
    return any(_cell_str(c) for c in row)


def row_has_column_a_data(row: List[Any] | None) -> bool:
    if not row:
        return False
    return bool(_cell_str(row[0] if row else ""))


def last_row_with_data_in_grid(values: List[List[Any]]) -> Optional[int]:
    """
    Última fila 1-based con dato en cualquier columna del rango devuelto por Sheets API.
    Coincide con len(values) cuando el rango empieza en fila 1 (A1:S…).
    """
    last: Optional[int] = None
    for i, row in enumerate(values or []):
        if row_has_cell_data(row):
            last = i + 1
    return last


def last_row_with_data_in_column_a(values: List[List[Any]]) -> Optional[int]:
    """Última fila 1-based con dato solo en columna A (numerador / lote)."""
    last: Optional[int] = None
    for i, row in enumerate(values or []):
        if row_has_column_a_data(row):
            last = i + 1
    return last


def _last_nonempty_sheet_row_in_column_values(
    values: List[List[Any]], *, row_start_1based: int
) -> Optional[int]:
    """Última fila del tramo con dato en cualquier columna A:S del slice (no solo A)."""
    last: Optional[int] = None
    for i, row in enumerate(values or []):
        if row_has_cell_data(row):
            last = row_start_1based + i
    return last


def audit_drive_sheet_row_continuity(
    db: Session, *, sample_limit: int = 15
) -> Dict[str, Any]:
    """
    Auditoría de huecos / solapes en ``drive`` tras sync manual o cron.

    - **Huecos de numeración:** faltan ``sheet_row_number`` entre min y max.
    - **Solapes de numeración:** el PK lo impide; se confirma count vs distinct.
    - **Filas vacías interiores:** filas A:S vacías entre la primera y la última
      con dato (huecos de contenido en la hoja).
    - **Solapes de cédula (col E):** misma cédula en más de una fila de Drive.
    """
    from collections import Counter

    lim = max(1, min(int(sample_limit), 50))
    nums = [
        int(n)
        for (n,) in db.execute(
            select(DriveRow.sheet_row_number).order_by(DriveRow.sheet_row_number.asc())
        ).all()
        if n is not None
    ]
    drive_count = len(nums)
    if drive_count == 0:
        return {
            "ok": True,
            "drive_row_count": 0,
            "huecos_numeracion": 0,
            "huecos_muestra": [],
            "solapes_numeracion": 0,
            "filas_vacias_interiores": 0,
            "filas_vacias_muestra": [],
            "cedulas_duplicadas": 0,
            "cedulas_duplicadas_muestra": [],
            "mensaje": "Tabla drive vacía: no hay filas que auditar.",
        }

    min_n, max_n = nums[0], nums[-1]
    expected = max_n - min_n + 1
    # Solapes: con PK no deberían existir; contamos repeticiones por seguridad.
    cnt = Counter(nums)
    solapes = sorted(n for n, c in cnt.items() if c > 1)
    present = set(nums)
    huecos = [i for i in range(min_n, max_n + 1) if i not in present]

    # Filas totalmente vacías en A:S (contenido).
    vacias_conds = [
        func.btrim(func.coalesce(getattr(DriveRow, f"col_{c}"), "")) == ""
        for c in "abcdefghijklmnopqrs"
    ]
    vacias_q = select(DriveRow.sheet_row_number).where(*vacias_conds)
    vacias = [int(n) for (n,) in db.execute(vacias_q).all() if n is not None]
    # Solo cuentan como hueco de contenido si están entre la primera y última fila con dato.
    con_dato = [n for n in nums if n not in set(vacias)]
    vacias_int: list[int] = []
    if con_dato:
        lo, hi = con_dato[0], con_dato[-1]
        vacias_int = [n for n in vacias if lo < n < hi]

    # Solapes de cédula (columna E).
    ced_rows = db.execute(
        select(DriveRow.sheet_row_number, DriveRow.col_e).where(
            DriveRow.col_e.isnot(None),
            func.btrim(DriveRow.col_e) != "",
        )
    ).all()
    by_ced: dict[str, list[int]] = {}
    for sr, raw in ced_rows:
        key = re.sub(r"\s+", "", str(raw or "").strip().upper())
        if not key:
            continue
        by_ced.setdefault(key, []).append(int(sr))
    dups = [
        {"cedula": k, "filas": sorted(v), "veces": len(v)}
        for k, v in by_ced.items()
        if len(v) > 1
    ]
    dups.sort(key=lambda x: (-x["veces"], x["cedula"]))

    ok = (
        not huecos
        and not solapes
        and drive_count == expected
        and len(vacias_int) == 0
    )
    partes: list[str] = []
    if huecos:
        partes.append(f"{len(huecos)} hueco(s) de numeración")
    if solapes:
        partes.append(f"{len(solapes)} solape(s) de sheet_row_number")
    if vacias_int:
        partes.append(f"{len(vacias_int)} fila(s) vacía(s) en medio de la hoja")
    if dups:
        partes.append(f"{len(dups)} cédula(s) repetida(s) en Drive")
    if not partes:
        partes.append(
            f"Continuo OK: filas {min_n}–{max_n} ({drive_count} filas, sin huecos ni solapes de número)."
        )

    return {
        "ok": ok and not dups,
        "drive_row_count": drive_count,
        "min_sheet_row": min_n,
        "max_sheet_row": max_n,
        "expected_count_si_continuo": expected,
        "huecos_numeracion": len(huecos),
        "huecos_muestra": huecos[:lim],
        "solapes_numeracion": len(solapes),
        "solapes_muestra": solapes[:lim],
        "filas_vacias_interiores": len(vacias_int),
        "filas_vacias_muestra": vacias_int[:lim],
        "cedulas_duplicadas": len(dups),
        "cedulas_duplicadas_muestra": dups[:lim],
        "mensaje": "; ".join(partes),
    }


def compute_scan_coverage_from_db(db: Session) -> Dict[str, Any]:
    """Métricas solo desde BD (sin llamar a Google)."""
    meta = get_conciliacion_sheet_meta(db)
    header_row = int(meta.header_row_index or 1) if meta else 1
    row_count_meta = int(meta.row_count or 0) if meta else 0
    expected_last = header_row + row_count_meta if row_count_meta > 0 else header_row

    max_row = db.scalar(select(func.max(DriveRow.sheet_row_number)))
    min_row = db.scalar(select(func.min(DriveRow.sheet_row_number)))
    drive_count = int(db.scalar(select(func.count()).select_from(DriveRow)) or 0)

    max_row_i = int(max_row) if max_row is not None else None
    min_row_i = int(min_row) if min_row is not None else None

    bd_coherente = (
        row_count_meta > 0
        and max_row_i is not None
        and max_row_i == expected_last
        and drive_count == row_count_meta
    )

    google_tail = meta_google_tail_row_number(meta, db)
    google_probed_at = meta_google_tail_row_probed_at_iso(meta, db)
    last_data_stored = meta_last_data_sheet_row_number(meta, db)

    cola_ok: Optional[bool] = None
    cola_mensaje: Optional[str] = None
    if google_tail is not None and max_row_i is not None:
        if google_tail > max_row_i:
            cola_ok = False
            cola_mensaje = (
                f"Google tiene datos en A:S hasta la fila {google_tail}, pero la BD solo hasta {max_row_i}. "
                "Ejecute sincronización manual con Drive."
            )
        elif google_tail < max_row_i:
            cola_ok = False
            cola_mensaje = (
                f"La BD marca última fila {max_row_i} pero en Google el rango A:S llega solo hasta {google_tail}. "
                "Revise cabecera LOTE o re-sincronice."
            )
        else:
            cola_ok = True
            cola_mensaje = (
                f"Cola alineada: última fila con dato en el rango A:S = {google_tail}."
            )

    auditoria_filas = audit_drive_sheet_row_continuity(db)

    return {
        "header_row_index": header_row,
        "data_row_count": row_count_meta,
        "expected_last_data_sheet_row": expected_last if row_count_meta > 0 else None,
        "last_data_sheet_row_stored": last_data_stored,
        "drive_min_sheet_row": min_row_i,
        "drive_max_sheet_row": max_row_i,
        "drive_row_count": drive_count,
        "bd_internally_consistent": bd_coherente,
        "google_tail_row_number": google_tail,
        "google_tail_row_probed_at": google_probed_at,
        "tail_aligned_with_drive_table": cola_ok,
        "tail_message": cola_mensaje,
        "drive_synced_at": meta.synced_at.isoformat() if meta and meta.synced_at else None,
        "auditoria_filas": auditoria_filas,
    }


def resolve_sync_end_row_from_column_a(
    spreadsheet_id: str,
    tab_name: str,
    *,
    marker: str = "LOTE",
    columns_range: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Paso previo al sync (nombre legacy): lee el rango A:S completo y detecta cabecera +
    última fila con dato en **cualquier** columna del rango (no solo A).

    Filas con nombre/cédula/teléfono/correo (D–G) pero columna A vacía quedaban fuera
    cuando solo se miraba A; el límite correcto es la cola del rango configurado.
    """
    from app.services.conciliacion_sheet_sync import (
        _find_header_row,
        fetch_sheet_values,
    )

    cols = (columns_range or getattr(settings, "CONCILIACION_SHEET_COLUMNS_RANGE", None) or "A:S").strip()
    sheet_title, values, _ncols = fetch_sheet_values(spreadsheet_id, tab_name, cols)
    if not values:
        raise ValueError(f"El rango {cols!r} de la hoja devolvió 0 filas.")

    h_idx, marker_hit = _find_header_row(values, marker)
    if not marker_hit:
        logger.warning(
            "[conciliacion_sheet_cobertura] Marcador %r no hallado en las primeras filas; cabecera índice 0.",
            marker,
        )

    sync_end_row = last_row_with_data_in_grid(values)
    last_in_a = last_row_with_data_in_column_a(values)
    if sync_end_row is None:
        raise ValueError(f"No hay filas con datos en el rango {cols!r}.")

    header_row_1based = h_idx + 1
    if sync_end_row < header_row_1based:
        raise ValueError(
            f"Última fila con dato ({sync_end_row}) está antes de la cabecera ({header_row_1based})."
        )
    if last_in_a is not None and last_in_a < sync_end_row:
        logger.warning(
            "[conciliacion_sheet_cobertura] Columna A solo hasta fila %s; rango %s hasta fila %s.",
            last_in_a,
            cols,
            sync_end_row,
        )

    logger.info(
        "[conciliacion_sheet_cobertura] rango %s: filas_api=%s cabecera_fila=%s ultima_fila_a=%s ultima_fila_%s=%s marker_hit=%s",
        cols,
        len(values),
        header_row_1based,
        last_in_a,
        cols,
        sync_end_row,
        marker_hit,
    )
    return {
        "sheet_title": sheet_title,
        "header_row_index": header_row_1based,
        "column_a_last_row": last_in_a or sync_end_row,
        "sync_end_row": sync_end_row,
        "marker_hit": marker_hit,
        "columns_range": cols,
        "grid_rows_returned": len(values),
        "prefetched_values": values,
    }


def probe_google_sheet_tail_row(
    db: Session,
    *,
    persist_meta: bool = True,
) -> Dict[str, Any]:
    """
    Lee un tramo del rango A:S (o columns_range) alrededor de la última fila conocida en BD
    y devuelve la última fila con contenido en cualquier columna del tramo.
    """
    from app.services.conciliacion_sheet_sync import fetch_sheet_values_slice

    spreadsheet_id = (getattr(settings, "CONCILIACION_SHEET_SPREADSHEET_ID", None) or "").strip()
    if not spreadsheet_id:
        raise ValueError("CONCILIACION_SHEET_SPREADSHEET_ID no está configurado.")

    tab_name = (getattr(settings, "CONCILIACION_SHEET_TAB_NAME", None) or "CONCILIACIÓN").strip()
    columns_range = (getattr(settings, "CONCILIACION_SHEET_COLUMNS_RANGE", None) or "A:S").strip()
    meta = get_conciliacion_sheet_meta(db)
    header_row = int(meta.header_row_index or 1) if meta else 1
    hint = db.scalar(select(func.max(DriveRow.sheet_row_number)))
    hint_i = int(hint) if hint is not None else header_row + int(meta.row_count or 0) if meta else header_row

    row_start = max(header_row + 1, hint_i - TAIL_PROBE_ROWS_ABOVE)
    row_end = hint_i + TAIL_PROBE_ROWS_BELOW
    from app.services.conciliacion_sheet_sync import _parse_columns_range

    col_start, col_end, _ncols_probe = _parse_columns_range(columns_range)
    probe_range_label = f"{col_start}{row_start}:{col_end}{row_end}"
    sheet_title = tab_name
    values: List[List[Any]] = []
    google_last: Optional[int] = None
    # Si la cola tiene datos hasta el final de la ventana, ampliar (filas nuevas bajo la última importada).
    for _ in range(4):
        sheet_title, values, _ncols = fetch_sheet_values_slice(
            spreadsheet_id,
            tab_name,
            columns_range,
            row_start,
            row_end,
        )
        google_last = _last_nonempty_sheet_row_in_column_values(
            values, row_start_1based=row_start
        )
        if google_last is not None and google_last >= row_end - 2:
            row_end += TAIL_PROBE_ROWS_BELOW
            continue
        break
    now = datetime.now(timezone.utc)

    if persist_meta and meta is not None:
        apply_scan_coverage_fields_to_meta(
            meta,
            db,
            google_tail_row_number=google_last,
            google_tail_row_probed_at=now,
        )
        meta.updated_at = now
        db.commit()

    coverage = compute_scan_coverage_from_db(db)
    logger.info(
        "[conciliacion_sheet_cobertura] probe tail sheet=%r rango=%s google_last=%s bd_max=%s",
        sheet_title,
        probe_range_label,
        google_last,
        coverage.get("drive_max_sheet_row"),
    )
    return {
        "ok": True,
        "sheet_title": sheet_title,
        "probe_range": probe_range_label,
        "probe_hint_row": hint_i,
        "google_tail_row_number": google_last,
        "probed_at": now.isoformat(),
        "scan_coverage": coverage,
    }


def record_last_data_row_on_meta(
    db: Session,
    *,
    last_data_sheet_row: int,
    run_tail_probe: bool = True,
) -> Dict[str, Any]:
    """Tras sync exitoso: guarda última fila de datos e intenta verificar cola en Google."""
    meta = get_conciliacion_sheet_meta(db)
    if meta is not None:
        apply_scan_coverage_fields_to_meta(
            meta,
            db,
            last_data_sheet_row_number=int(last_data_sheet_row),
        )
        meta.updated_at = datetime.now(timezone.utc)
        db.flush()

    out: Dict[str, Any] = {
        "last_data_sheet_row_number": int(last_data_sheet_row),
        "tail_probe": None,
    }
    if run_tail_probe:
        try:
            out["tail_probe"] = probe_google_sheet_tail_row(db, persist_meta=True)
        except Exception as e:
            logger.warning(
                "[conciliacion_sheet_cobertura] tail probe tras sync falló: %s",
                e,
            )
            out["tail_probe"] = {"ok": False, "error": str(e)[:500]}
    out["scan_coverage"] = compute_scan_coverage_from_db(db)
    return out
