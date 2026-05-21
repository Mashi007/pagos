"""
Acceso seguro a conciliacion_sheet_meta cuando faltan columnas de cobertura (migración pendiente).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session, load_only

from app.models.conciliacion_sheet import ConciliacionSheetMeta

_META_CORE_ATTRS = (
    ConciliacionSheetMeta.id,
    ConciliacionSheetMeta.spreadsheet_id,
    ConciliacionSheetMeta.sheet_title,
    ConciliacionSheetMeta.headers,
    ConciliacionSheetMeta.header_row_index,
    ConciliacionSheetMeta.row_count,
    ConciliacionSheetMeta.col_count,
    ConciliacionSheetMeta.synced_at,
    ConciliacionSheetMeta.last_error,
    ConciliacionSheetMeta.updated_at,
)


def conciliacion_meta_scan_columns_available(db: Session) -> bool:
    """True si la BD ya tiene last_data_sheet_row_number / google_tail_*."""
    bind = db.get_bind()
    try:
        names = {c["name"] for c in sa_inspect(bind).get_columns("conciliacion_sheet_meta")}
    except Exception:
        return False
    return "last_data_sheet_row_number" in names


def get_conciliacion_sheet_meta(db: Session, meta_id: int = 1) -> Optional[ConciliacionSheetMeta]:
    """
    Carga meta id=1 sin fallar si faltan columnas añadidas en 071_conciliacion_sheet_scan_coverage.
    """
    if conciliacion_meta_scan_columns_available(db):
        return db.get(ConciliacionSheetMeta, meta_id)
    return (
        db.query(ConciliacionSheetMeta)
        .options(load_only(*_META_CORE_ATTRS))
        .filter(ConciliacionSheetMeta.id == meta_id)
        .first()
    )


def apply_scan_coverage_fields_to_meta(
    meta: ConciliacionSheetMeta,
    db: Session,
    *,
    last_data_sheet_row_number: Optional[int] = None,
    google_tail_row_number: Optional[int] = None,
    google_tail_row_probed_at=None,
) -> None:
    """Persiste campos de cobertura solo si existen en la BD."""
    if not conciliacion_meta_scan_columns_available(db):
        return
    if last_data_sheet_row_number is not None:
        meta.last_data_sheet_row_number = int(last_data_sheet_row_number)
    if google_tail_row_number is not None:
        meta.google_tail_row_number = google_tail_row_number
    if google_tail_row_probed_at is not None:
        meta.google_tail_row_probed_at = google_tail_row_probed_at
