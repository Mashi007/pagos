"""
Sincronización de la hoja CONCILIACIÓN (Google Sheets) → BD.

- POST /conciliacion-sheet/sync — para cron (ej. 03:00 America/Caracas). Header X-Conciliacion-Sheet-Sync-Secret.
- POST /conciliacion-sheet/sync-now — mismo trabajo que /sync, pero con sesión staff (admin / operador / gerente).
- GET /conciliacion-sheet/status — metadatos, última corrida y si el snapshot alcanza para GET …/exportar/fecha-drive.

En Render u otro hosting: programar HTTP POST diario a la hora equivalente en UTC
(03:00 Caracas ≈ 07:00 UTC, sin DST en Venezuela).

Por defecto solo se importan columnas A:S (variable CONCILIACION_SHEET_COLUMNS_RANGE).
"""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.database import BUSINESS_TIMEZONE
from app.core.database import get_db
from app.core.deps import get_current_user, require_admin_or_operator
from app.core.config import settings
from app.models.conciliacion_sheet import (
    ConciliacionSheetMeta,
    ConciliacionSheetRow,
    ConciliacionSheetSyncRun,
)
from app.schemas.auth import UserResponse
from app.services.conciliacion_sheet_sync import run_sync_to_db

logger = logging.getLogger(__name__)

router = APIRouter()


def _require_sync_secret(x_secret: Optional[str]) -> None:
    expected = (getattr(settings, "CONCILIACION_SHEET_SYNC_SECRET", None) or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CONCILIACION_SHEET_SYNC_SECRET no configurado en el servidor.",
        )
    got = (x_secret or "").strip()
    if got != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Secreto inválido.")


@router.post("/sync")
def post_sync_conciliacion_sheet(
    db: Session = Depends(get_db),
    x_conciliacion_sheet_sync_secret: Optional[str] = Header(None, alias="X-Conciliacion-Sheet-Sync-Secret"),
) -> Dict[str, Any]:
    logger.info("[conciliacion_sheet] POST /sync (cron / secreto)")
    _require_sync_secret(x_conciliacion_sheet_sync_secret)
    try:
        return run_sync_to_db(db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.exception("post_sync_conciliacion_sheet: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)[:500] if e else "Error al sincronizar",
        ) from e


@router.post("/sync-now")
def post_sync_conciliacion_sheet_now(
    db: Session = Depends(get_db),
    _staff: UserResponse = Depends(require_admin_or_operator),
) -> Dict[str, Any]:
    """
    Descarga la pestaña CONCILIACIÓN desde Google Sheets con las credenciales del servidor
    (Informe de pagos / Gmail) y reemplaza el snapshot en BD. Mismo cuerpo que POST /sync.
    """
    logger.info(
        "[conciliacion_sheet] POST /sync-now usuario_id=%s rol=%s",
        getattr(_staff, "id", None),
        getattr(_staff, "rol", None),
    )
    try:
        return run_sync_to_db(db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        logger.exception("post_sync_conciliacion_sheet_now: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e)[:500] if e else "Error al sincronizar",
        ) from e


# Columna Q = índice 16: hace falta al menos 17 cabeceras (A..Q) para el reporte Fecha Drive.
_MIN_HEADERS_FOR_FECHA_DRIVE = 17


@router.get("/status")
def get_conciliacion_sheet_status(
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    meta = db.get(ConciliacionSheetMeta, 1)
    last_run = db.execute(
        select(ConciliacionSheetSyncRun).order_by(desc(ConciliacionSheetSyncRun.id)).limit(1)
    ).scalars().first()
    cols_range = (getattr(settings, "CONCILIACION_SHEET_COLUMNS_RANGE", None) or "A:S").strip()
    spreadsheet_configured = bool(
        (getattr(settings, "CONCILIACION_SHEET_SPREADSHEET_ID", None) or "").strip()
    )
    snapshot_row_count = int(
        db.execute(select(func.count()).select_from(ConciliacionSheetRow)).scalar_one() or 0
    )
    hdrs = list(meta.headers) if meta and meta.headers else []
    headers_ok = len(hdrs) >= _MIN_HEADERS_FOR_FECHA_DRIVE
    fecha_drive_ready = (
        spreadsheet_configured
        and bool(hdrs)
        and headers_ok
        and snapshot_row_count > 0
    )
    logger.info(
        "[conciliacion_sheet] GET /status fecha_drive_ready=%s filas_snapshot=%s n_headers=%s",
        fecha_drive_ready,
        snapshot_row_count,
        len(hdrs),
    )
    return {
        "timezone": BUSINESS_TIMEZONE,
        "columns_range": cols_range,
        "spreadsheet_configured": spreadsheet_configured,
        "expected_tab_name": (getattr(settings, "CONCILIACION_SHEET_TAB_NAME", None) or "CONCILIACIÓN").strip(),
        "snapshot_row_count": snapshot_row_count,
        "fecha_drive_ready": fecha_drive_ready,
        "fecha_drive_hint": (
            None
            if fecha_drive_ready
            else (
                "Configure CONCILIACION_SHEET_SPREADSHEET_ID y credenciales Google; "
                "luego use POST /conciliacion-sheet/sync-now o el cron con /sync. "
                "Se requiere pestaña con cabecera hasta columna Q y filas de datos."
                if spreadsheet_configured
                else "Falta CONCILIACION_SHEET_SPREADSHEET_ID en el servidor."
            )
        ),
        "meta": None
        if meta is None
        else {
            "spreadsheet_id": meta.spreadsheet_id,
            "sheet_title": meta.sheet_title,
            "header_row_index": meta.header_row_index,
            "row_count": meta.row_count,
            "col_count": meta.col_count,
            "headers": meta.headers,
            "synced_at": meta.synced_at.isoformat() if meta.synced_at else None,
            "last_error": meta.last_error,
            "updated_at": meta.updated_at.isoformat() if meta.updated_at else None,
        },
        "last_run": None
        if last_run is None
        else {
            "id": last_run.id,
            "started_at": last_run.started_at.isoformat() if last_run.started_at else None,
            "finished_at": last_run.finished_at.isoformat() if last_run.finished_at else None,
            "success": last_run.success,
            "message": last_run.message,
            "row_count": last_run.row_count,
            "col_count": last_run.col_count,
            "duration_ms": last_run.duration_ms,
        },
    }
