"""
Endpoints para el pipeline Gmail -> Drive -> Gemini -> Sheets (módulo Pagos).
La información a extraer puede estar en adjuntos al correo o en imágenes en el cuerpo del email
(partes MIME inline o imágenes embebidas en HTML como data:image/...;base64,...).
- POST /pagos/gmail/run-now: ejecutar pipeline ahora
- GET /pagos/gmail/download-excel: descargar Excel del día (datos del Sheet del día)
- GET /pagos/gmail/status: última ejecución y próxima programada (cron cada 15 min en segundo plano)
- POST /pagos/gmail/confirmar-dia: confirmación sí/no; si sí, se borran los datos del día (el Excel quedará vacío para esa fecha).
"""
import io
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import and_, delete, desc, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem
from app.services.pagos_gmail.credentials import log_pagos_gmail_config_status
from app.services.pagos_gmail.pipeline import run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


def _is_pipeline_running(db: Session) -> bool:
    """True si hay una sync en estado running iniciada en los últimos N minutos (2× intervalo del cron)."""
    from app.core.config import settings
    cron_min = settings.PAGOS_GMAIL_CRON_MINUTES
    cutoff = datetime.utcnow() - timedelta(minutes=max(12, cron_min * 2))
    row = db.execute(
        select(PagosGmailSync).where(
            and_(
                PagosGmailSync.status == "running",
                PagosGmailSync.started_at >= cutoff,
            )
        ).limit(1)
    ).scalars().first()
    return row is not None


def _last_run_too_recent(db: Session) -> tuple[bool, Optional[int]]:
    """
    True si la última ejecución (terminada) fue hace menos del intervalo mínimo.
    Evita procesar email cuando aún no es tiempo (respetar PAGOS_GMAIL_CRON_MINUTES).
    Returns (too_recent, minutes_to_wait).
    """
    from app.core.config import settings
    cron_min = settings.PAGOS_GMAIL_CRON_MINUTES
    min_gap = max(5, cron_min - 2)
    last = db.execute(
        select(PagosGmailSync)
        .where(PagosGmailSync.finished_at.isnot(None))
        .order_by(desc(PagosGmailSync.finished_at))
        .limit(1)
    ).scalars().first()
    if not last or not last.finished_at:
        return False, None
    elapsed = (datetime.utcnow() - last.finished_at).total_seconds() / 60
    if elapsed < min_gap:
        wait = max(0, int(min_gap - elapsed))
        return True, wait
    return False, None


@router.post("/run-now")
def run_now(force: bool = True, db: Session = Depends(get_db)):
    """Ejecuta el pipeline una vez (Gmail -> Drive -> Gemini -> Sheets). Por defecto force=True (ejecución manual desde la UI); con force=false se respeta el intervalo mínimo."""
    if _is_pipeline_running(db):
        raise HTTPException(
            status_code=409,
            detail="Ya hay una sincronización en curso. Espere unos minutos.",
        )
    if force is False:
        too_recent, wait_min = _last_run_too_recent(db)
        if too_recent and wait_min is not None:
            raise HTTPException(
                status_code=429,
                detail=f"Aún no es tiempo de procesar. La última ejecución fue hace poco. Espere {wait_min} min (intervalo: PAGOS_GMAIL_CRON_MINUTES).",
            )
    sync_id, status = run_pipeline(db)
    if status == "no_credentials":
        log_pagos_gmail_config_status()
        raise HTTPException(
            status_code=503,
            detail=(
                "Credenciales OAuth inválidas (Google devolvió 'invalid_client'). "
                "Vaya a Configuración > Informe de pagos: pegue el mismo Client ID y Client secret que en Google Cloud, guarde, "
                "y luego pulse «Conectar con Google» para obtener un nuevo token. Sin reconectar, el token antiguo no funciona con el secret nuevo."
            ),
        )
    return {"sync_id": sync_id, "status": status}


@router.get("/status")
def status(db: Session = Depends(get_db)):
    """Última ejecución y próxima (intervalo configurable vía PAGOS_GMAIL_CRON_MINUTES)."""
    last = db.execute(select(PagosGmailSync).order_by(desc(PagosGmailSync.started_at)).limit(1)).scalars().first()
    from app.core.config import settings
    cron_min = settings.PAGOS_GMAIL_CRON_MINUTES
    next_at = None
    if last and last.started_at:
        next_at = last.started_at + timedelta(minutes=cron_min)
    return {
        "last_run": last.started_at.isoformat() if last and last.started_at else None,
        "last_status": last.status if last else None,
        "last_emails": last.emails_processed if last else 0,
        "last_files": last.files_processed if last else 0,
        "next_run_approx": next_at.isoformat() if next_at else None,
    }


def _get_sheet_date_for_download() -> datetime:
    """Después de las 23:50 (America/Caracas) se considera el día siguiente."""
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Caracas")
    now = datetime.now(tz)
    base = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if now.hour == 23 and now.minute >= 50:
        base += timedelta(days=1)
    return base.replace(tzinfo=None)


def _sheet_date_from_fecha(fecha: Optional[str]) -> datetime:
    """Convierte fecha opcional 'YYYY-MM-DD' a datetime (00:00:00); si no, usa lógica del día actual."""
    if not fecha or not fecha.strip():
        return _get_sheet_date_for_download()
    try:
        return datetime.strptime(fecha.strip()[:10], "%Y-%m-%d")
    except ValueError:
        return _get_sheet_date_for_download()


class ConfirmarDiaBody(BaseModel):
    """Respuesta simple sí/no: si confirmado=true se borran los datos del día."""
    confirmado: bool
    fecha: Optional[str] = None  # YYYY-MM-DD; si no se envía, se usa el día actual (misma lógica que download)


@router.post("/confirmar-dia", response_model=dict)
def confirmar_dia(body: ConfirmarDiaBody = Body(...), db: Session = Depends(get_db)):
    """
    Confirmación desde la interfaz (sí/no). Si confirmado=true, se borran los ítems del día
    en la BD para esa fecha; el Excel de ese día quedará vacío en futuras descargas.
    Si confirmado=false no se hace nada.
    """
    if not body.confirmado:
        return {"confirmado": False, "mensaje": "Sin cambios. Los datos del día se mantienen."}
    from app.services.pagos_gmail.helpers import get_sheet_name_for_date
    sheet_date = _sheet_date_from_fecha(body.fecha)
    sheet_name = get_sheet_name_for_date(sheet_date)
    result = db.execute(delete(PagosGmailSyncItem).where(PagosGmailSyncItem.sheet_name == sheet_name))
    db.commit()
    deleted = result.rowcount if hasattr(result, "rowcount") else 0
    logger.info("Pagos Gmail confirmar-dia: confirmado=True, fecha=%s, sheet_name=%s, borrados=%s", sheet_date.date(), sheet_name, deleted)
    return {
        "confirmado": True,
        "fecha": sheet_date.strftime("%Y-%m-%d"),
        "sheet_name": sheet_name,
        "borrados": deleted,
        "mensaje": f"Datos del día {sheet_date.strftime('%Y-%m-%d')} borrados." if deleted else f"No había datos para el día {sheet_date.strftime('%Y-%m-%d')}.",
    }


@router.get("/download-excel")
def download_excel(db: Session = Depends(get_db)):
    """
    Genera y devuelve un Excel con los ítems del día (según lógica 23:50 America/Caracas).
    Columnas: Asunto, Fecha Pago, Cédula, Monto, Referencia, Link (para carga masiva).
    Los datos provienen del pipeline Gmail -> Drive -> Gemini -> Sheets: ejecute POST /run-now
    y tenga GEMINI_API_KEY configurado para que Gemini extraiga fecha, cédula, monto y referencia
    de cada adjunto (imagen/PDF). Si no hay ítems para la fecha, se añade una fila informativa.
    """
    from openpyxl import Workbook
    from app.services.pagos_gmail.helpers import get_sheet_name_for_date
    sheet_date = _get_sheet_date_for_download()
    sheet_name = get_sheet_name_for_date(sheet_date)
    items = db.execute(
        select(PagosGmailSyncItem)
        .join(PagosGmailSync, PagosGmailSyncItem.sync_id == PagosGmailSync.id)
        .where(PagosGmailSyncItem.sheet_name == sheet_name)
        .order_by(PagosGmailSyncItem.created_at)
    ).scalars().all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Pagos"
    ws.append(["Asunto", "Fecha Pago", "Cedula", "Monto", "Referencia", "Link"])
    if not items:
        # Sin ítems: el pipeline no ha procesado correos para esta fecha o no se ha ejecutado.
        # Añadir una fila informativa para que el Excel no llegue solo con cabeceras.
        ws.append([
            f"Sin datos para {sheet_date.strftime('%Y-%m-%d')}. Ejecute el pipeline (Gmail -> Gemini -> Sheets) y asegúrese de tener GEMINI_API_KEY configurado.",
            "",
            "",
            "",
            "",
            "",
        ])
    for it in items:
        ws.append([
            (getattr(it, "asunto", None) or it.correo_origen) or "",
            it.fecha_pago or "",
            it.cedula or "",
            it.monto or "",
            it.numero_referencia or "",
            it.drive_link or "",
        ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"Pagos_Gmail_{sheet_date.strftime('%Y-%m-%d')}.xlsx"
    return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={filename}"})
