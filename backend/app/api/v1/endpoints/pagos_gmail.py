"""
Endpoints para el pipeline Gmail -> Drive -> Gemini -> Sheets (módulo Pagos).
La información a extraer puede estar en adjuntos al correo o en imágenes en el cuerpo del email
(partes MIME inline o imágenes embebidas en HTML como data:image/...;base64,...).
- POST /pagos/gmail/run-now: ejecutar pipeline ahora
- GET /pagos/gmail/download-excel: descargar Excel del día (datos del Sheet del día)
- GET /pagos/gmail/status: última ejecución y próxima programada
"""
import io
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem
from app.services.pagos_gmail.credentials import log_pagos_gmail_config_status
from app.services.pagos_gmail.pipeline import run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


def _is_pipeline_running(db: Session) -> bool:
    """True si hay una sync en estado running iniciada en los últimos 12 minutos."""
    cutoff = datetime.utcnow() - timedelta(minutes=12)
    row = db.execute(
        select(PagosGmailSync).where(
            and_(
                PagosGmailSync.status == "running",
                PagosGmailSync.started_at >= cutoff,
            )
        ).limit(1)
    ).scalars().first()
    return row is not None


@router.post("/run-now")
def run_now(db: Session = Depends(get_db)):
    """Ejecuta el pipeline una vez (Gmail -> Drive -> Gemini -> Sheets)."""
    if _is_pipeline_running(db):
        raise HTTPException(
            status_code=409,
            detail="Ya hay una sincronización en curso. Espere unos minutos.",
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
    """Última ejecución y próxima (cron cada 15 min)."""
    last = db.execute(select(PagosGmailSync).order_by(desc(PagosGmailSync.started_at)).limit(1)).scalars().first()
    from app.core.config import settings
    cron_min = getattr(settings, "PAGOS_GMAIL_CRON_MINUTES", 15)
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


@router.get("/download-excel")
def download_excel(db: Session = Depends(get_db)):
    """
    Genera y devuelve un Excel con los ítems del día (según lógica 23:50 America/Caracas).
    Columnas: Correo Origen, Fecha Pago, Cédula, Monto, Referencia, Link (para carga masiva).
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
    ws.append(["Correo Origen", "Fecha Pago", "Cedula", "Monto", "Referencia", "Link"])
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
            it.correo_origen or "",
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
