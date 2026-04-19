"""
Sincronización de la hoja CONCILIACIÓN (Google Sheets) → BD.

- POST /conciliacion-sheet/sync — cron externo (p. ej. Render Cron Jobs) con header X-Conciliacion-Sheet-Sync-Secret.
  Horario recomendado alineado al job interno: domingo y miércoles 02:00 America/Caracas (≈ 06:00 UTC, sin DST).
  Si ENABLE_AUTOMATIC_SCHEDULED_JOBS=true, el APScheduler del backend ya ejecuta el mismo sync esos días a esa hora:
  puede omitir el cron externo o dejarlo como respaldo (evite disparos redundantes minuto a minuto).
  Tras ese snapshot, el backend (si ENABLE_AUTOMATIC_SCHEDULED_JOBS=true) materializa a las 03:00 la lista de
  candidatos «Clientes (Drive)» en BD; cron externo no es necesario para esa lista (ver POST /clientes/drive-import/refresh-cache).
- POST /conciliacion-sheet/sync-now — mismo trabajo que /sync, pero con sesión staff (admin / operador / gerente).
- GET /conciliacion-sheet/status — metadatos, última corrida y si el snapshot alcanza para GET …/exportar/fecha-drive.

Por defecto solo se importan columnas A:S (variable CONCILIACION_SHEET_COLUMNS_RANGE).
Cada sync exitoso también rellena la tabla drive (columnas col_a..col_s).
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

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
from app.models.drive import DriveRow
from app.schemas.auth import UserResponse
from app.services.conciliacion_sheet_sync import (
    build_conciliacion_sheet_diagnostico,
    run_sync_to_db,
)

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


def _fecha_drive_hint_and_blocker(
    *,
    fecha_drive_ready: bool,
    spreadsheet_configured: bool,
    cols_range: str,
    hdrs: List[str],
    headers_ok: bool,
    snapshot_row_count: int,
    last_run: Optional[ConciliacionSheetSyncRun],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Texto para operadores (fecha_drive_hint) y código estable (fecha_drive_blocker)
    cuando Fecha Drive aún no está listo.
    """
    if fecha_drive_ready:
        return None, None

    min_h = _MIN_HEADERS_FOR_FECHA_DRIVE
    n_headers = len(hdrs)

    if not spreadsheet_configured:
        return (
            "Falta CONCILIACION_SHEET_SPREADSHEET_ID en el servidor (Render / .env).",
            "no_spreadsheet_id",
        )

    if last_run is None:
        return (
            "No hay ninguna corrida de sincronización registrada en la base de datos. "
            "Ejecute POST /api/v1/conciliacion-sheet/sync-now (personal autorizado) "
            "o programe POST /api/v1/conciliacion-sheet/sync con el secreto del cron.",
            "never_synced",
        )

    if not last_run.success:
        msg = (last_run.message or "").strip().replace("\n", " ")
        if len(msg) > 220:
            msg = msg[:217] + "..."
        tail = f" Detalle: {msg}" if msg else ""
        return (
            "La última sincronización desde Google Sheets falló. Revise credenciales "
            "(Informe de pagos / Gmail), nombre de la pestaña, ID del documento y permisos "
            f"de la cuenta ante el spreadsheet.{tail}",
            "last_sync_failed",
        )

    if (last_run.row_count or 0) == 0:
        return (
            "La última sincronización terminó en OK pero importó 0 filas de datos. Revise que "
            "la pestaña sea la esperada, que exista la fila de cabecera (marcador LOTE), el "
            "rango de columnas y que haya filas debajo de la cabecera.",
            "sync_ok_zero_rows",
        )

    if not headers_ok:
        return (
            f"Las cabeceras guardadas ({n_headers}) no alcanzan la columna Q (se necesitan al "
            f"menos {min_h}). Amplíe CONCILIACION_SHEET_COLUMNS_RANGE (ahora {cols_range!r}).",
            "headers_below_Q",
        )

    if snapshot_row_count == 0:
        if (last_run.row_count or 0) > 0:
            return (
                "La última sync reportó filas importadas pero el snapshot en BD está vacío; "
                "reintente sync-now o revise integridad de datos.",
                "snapshot_inconsistent",
            )
        return (
            "No hay filas en el snapshot (tabla conciliacion_sheet_rows). Ejecute sync-now o el cron.",
            "empty_snapshot",
        )

    return (
        "Aún no es posible generar Fecha Drive. Ejecute sync-now o revise la configuración.",
        "unknown",
    )


def _build_operator_checklist(
    *,
    fecha_drive_ready: bool,
    spreadsheet_configured: bool,
    sync_secret_configured: bool,
    scheduled_jobs_enabled: bool,
    blocker: Optional[str],
) -> List[str]:
    """Pasos concretos para quien despliega (Render / .env). Vacío si ya está listo."""
    if fecha_drive_ready:
        return []

    out: List[str] = [
        "En el servicio de API (backend), defina CONCILIACION_SHEET_SPREADSHEET_ID con el ID del Google Sheet "
        "(fragmento entre /d/ y /edit en la URL). Sin esto no hay lectura de la hoja.",
        "Confirme que la cuenta usada por Informe de pagos / Gmail en el servidor tenga permiso de lectura sobre ese documento.",
        "Guarde variables en Render (o .env) y reinicie o redeploy del backend.",
        "Con personal autorizado: use el botón «Traer hoja desde Drive ahora» o POST /api/v1/conciliacion-sheet/sync-now.",
    ]
    if not sync_secret_configured:
        out.append(
            "Opcional — cron sin sesión: defina CONCILIACION_SHEET_SYNC_SECRET y llame "
            "POST /api/v1/conciliacion-sheet/sync con el header X-Conciliacion-Sheet-Sync-Secret."
        )
    else:
        out.append(
            "Cron: programe POST /api/v1/conciliacion-sheet/sync con el secreto, o deje activo el job interno (ver siguiente punto)."
        )
    if not scheduled_jobs_enabled:
        out.append(
            "Si ENABLE_AUTOMATIC_SCHEDULED_JOBS=false, el job diario 04:01 (America/Caracas) no arranca en el servidor; "
            "use cron externo (Render Cron, etc.) o sync manual."
        )
    else:
        out.append(
            "Con ENABLE_AUTOMATIC_SCHEDULED_JOBS=true el scheduler ejecuta la sync de la hoja a las 04:01 (America/Caracas)."
        )
    if blocker == "headers_below_Q":
        out.append(
            "Amplíe CONCILIACION_SHEET_COLUMNS_RANGE para incluir al menos hasta la columna Q y vuelva a sincronizar."
        )
    elif blocker == "last_sync_failed":
        out.append("Revise el detalle de la última corrida (last_run.message) y corrija credenciales, pestaña o permisos.")
    elif blocker == "sync_ok_zero_rows":
        out.append(
            "La hoja devolvió 0 filas de datos: verifique pestaña CONCILIACIÓN, fila de cabecera con marcador LOTE y datos debajo."
        )
    elif blocker == "never_synced" and spreadsheet_configured:
        out.append("Aún no hay corridas en BD: ejecute al menos una vez sync-now o POST /sync con secreto.")
    return out


@router.get("/diagnostico")
def get_conciliacion_sheet_diagnostico(
    db: Session = Depends(get_db),
    _user: UserResponse = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    JSON agregado: variables de entorno (enmascaradas), filas en BD, última corrida y
    ping ligero a la API de Google (solo metadatos del libro). No escribe en Drive ni en BD.
    """
    logger.info("[conciliacion_sheet] GET /diagnostico")
    return build_conciliacion_sheet_diagnostico(db)


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
    drive_row_count = int(db.execute(select(func.count()).select_from(DriveRow)).scalar_one() or 0)
    hdrs = list(meta.headers) if meta and meta.headers else []
    headers_ok = len(hdrs) >= _MIN_HEADERS_FOR_FECHA_DRIVE
    fecha_drive_ready = (
        spreadsheet_configured
        and bool(hdrs)
        and headers_ok
        and snapshot_row_count > 0
    )
    hint, blocker = _fecha_drive_hint_and_blocker(
        fecha_drive_ready=fecha_drive_ready,
        spreadsheet_configured=spreadsheet_configured,
        cols_range=cols_range,
        hdrs=hdrs,
        headers_ok=headers_ok,
        snapshot_row_count=snapshot_row_count,
        last_run=last_run,
    )
    sync_secret_configured = bool(
        (getattr(settings, "CONCILIACION_SHEET_SYNC_SECRET", None) or "").strip()
    )
    scheduled_jobs_enabled = bool(getattr(settings, "ENABLE_AUTOMATIC_SCHEDULED_JOBS", False))
    operator_checklist = _build_operator_checklist(
        fecha_drive_ready=fecha_drive_ready,
        spreadsheet_configured=spreadsheet_configured,
        sync_secret_configured=sync_secret_configured,
        scheduled_jobs_enabled=scheduled_jobs_enabled,
        blocker=blocker,
    )
    logger.info(
        "[conciliacion_sheet] GET /status fecha_drive_ready=%s filas_snapshot=%s filas_drive=%s n_headers=%s "
        "blocker=%s last_run_id=%s last_run_ok=%s last_run_rows=%s",
        fecha_drive_ready,
        snapshot_row_count,
        drive_row_count,
        len(hdrs),
        blocker,
        getattr(last_run, "id", None),
        getattr(last_run, "success", None),
        getattr(last_run, "row_count", None),
    )
    return {
        "timezone": BUSINESS_TIMEZONE,
        "columns_range": cols_range,
        "spreadsheet_configured": spreadsheet_configured,
        "expected_tab_name": (getattr(settings, "CONCILIACION_SHEET_TAB_NAME", None) or "CONCILIACIÓN").strip(),
        "snapshot_row_count": snapshot_row_count,
        "drive_row_count": drive_row_count,
        "fecha_drive_ready": fecha_drive_ready,
        "fecha_drive_blocker": blocker,
        "fecha_drive_hint": hint,
        "sync_secret_configured": sync_secret_configured,
        "scheduled_jobs_enabled": scheduled_jobs_enabled,
        "operator_checklist": operator_checklist,
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
