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

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import and_, delete, desc, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem
from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials, log_pagos_gmail_config_status
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


def _run_pipeline_background(sync_id: int) -> None:
    """Ejecuta el pipeline en background con su propia sesión de BD (evita el timeout de 30s de Render/Axios)."""
    db = SessionLocal()
    try:
        run_pipeline(db, existing_sync_id=sync_id)
    except Exception as e:
        logger.exception("[PAGOS_GMAIL] Error en background pipeline (sync_id=%s): %s", sync_id, e)
        try:
            sync = db.execute(select(PagosGmailSync).where(PagosGmailSync.id == sync_id)).scalars().first()
            if sync and sync.status == "running":
                sync.status = "error"
                sync.finished_at = datetime.utcnow()
                sync.error_message = str(e)[:2000]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/run-now")
def run_now(background_tasks: BackgroundTasks, force: bool = True, db: Session = Depends(get_db)):
    """
    Inicia el pipeline en segundo plano (Gmail -> Drive -> Gemini -> Sheets) y devuelve inmediatamente.
    El frontend debe hacer polling a GET /status hasta que last_status sea 'success' o 'error'.
    Por defecto force=True (ejecución manual desde la UI); con force=false se respeta el intervalo mínimo.
    """
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
    # Verificar credenciales de forma síncrona (respuesta inmediata si fallan)
    creds = get_pagos_gmail_credentials()
    if not creds:
        log_pagos_gmail_config_status()
        raise HTTPException(
            status_code=503,
            detail=(
                "Credenciales OAuth inválidas (Google devolvió 'invalid_client'). "
                "Vaya a Configuración > Informe de pagos: pegue el mismo Client ID y Client secret que en Google Cloud, guarde, "
                "y luego pulse «Conectar con Google» para obtener un nuevo token. Sin reconectar, el token antiguo no funciona con el secret nuevo."
            ),
        )
    # Crear registro de sync de inmediato (evita que un segundo click arranque otro pipeline)
    sync = PagosGmailSync(status="running", emails_processed=0, files_processed=0)
    db.add(sync)
    db.commit()
    db.refresh(sync)
    sync_id = sync.id
    # Lanzar pipeline en segundo plano; el cliente hace polling a /status
    background_tasks.add_task(_run_pipeline_background, sync_id)
    return {
        "sync_id": sync_id,
        "status": "running",
        "emails_processed": 0,
        "files_processed": 0,
    }


@router.get("/status")
def status(db: Session = Depends(get_db)):
    """Última ejecución, próxima y última fecha con datos disponibles para descargar."""
    last = db.execute(select(PagosGmailSync).order_by(desc(PagosGmailSync.started_at)).limit(1)).scalars().first()
    from app.core.config import settings
    cron_min = settings.PAGOS_GMAIL_CRON_MINUTES
    next_at = None
    if last and last.started_at:
        next_at = last.started_at + timedelta(minutes=cron_min)
    latest_data_date = _get_latest_date_with_data(db)
    return {
        "last_run": last.started_at.isoformat() if last and last.started_at else None,
        "last_status": last.status if last else None,
        "last_emails": last.emails_processed if last else 0,
        "last_files": last.files_processed if last else 0,
        "next_run_approx": next_at.isoformat() if next_at else None,
        "latest_data_date": latest_data_date,  # fecha más reciente con datos para descargar
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


def _find_sheet_date_with_data(db: Session, from_date: datetime, max_days_back: int = 30) -> tuple[Optional[datetime], list]:
    """
    Busca la fecha más reciente con datos, probando from_date y hasta max_days_back días anteriores.
    El lookback amplio (30 días por defecto) cubre correos del backlog recibidos semanas atrás.
    Devuelve (sheet_date, items) si hay datos; si no, (None, []).
    """
    from app.services.pagos_gmail.helpers import get_sheet_name_for_date
    for delta in range(max_days_back + 1):
        d = from_date - timedelta(days=delta)
        sheet_name = get_sheet_name_for_date(d)
        items = db.execute(
            select(PagosGmailSyncItem)
            .join(PagosGmailSync, PagosGmailSyncItem.sync_id == PagosGmailSync.id)
            .where(PagosGmailSyncItem.sheet_name == sheet_name)
            .order_by(PagosGmailSyncItem.created_at)
        ).scalars().all()
        if items:
            return d, items
    return None, []


def _get_latest_date_with_data(db: Session) -> Optional[str]:
    """Devuelve la fecha (YYYY-MM-DD) del ítem más reciente, útil para guiar al usuario."""
    from app.services.pagos_gmail.helpers import get_sheet_name_for_date
    from datetime import datetime as dt
    item = db.execute(
        select(PagosGmailSyncItem)
        .join(PagosGmailSync, PagosGmailSyncItem.sync_id == PagosGmailSync.id)
        .order_by(desc(PagosGmailSyncItem.created_at))
        .limit(1)
    ).scalars().first()
    if not item or not item.created_at:
        return None
    # sheet_name tiene formato Pagos_Cobros_9Marzo2026 → extraer fecha del created_at
    return item.created_at.strftime("%Y-%m-%d")


@router.get("/download-excel")
def download_excel(fecha: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Genera y devuelve un Excel con los ítems del día. Por defecto usa la fecha actual (America/Caracas; después de 23:50 se considera el día siguiente).
    Si no hay datos para esa fecha, busca en los 3 días anteriores (evita desajuste por zona horaria o fecha del correo).
    Opcional: ?fecha=YYYY-MM-DD para descargar un día concreto.
    Si no hay datos en ninguna fecha reciente, devuelve 404 con mensaje claro (no se descarga un Excel vacío).
    Columnas: Asunto, Fecha Pago, Cédula, Monto, Referencia, Link.
    """
    from openpyxl import Workbook
    from app.services.pagos_gmail.helpers import get_sheet_name_for_date
    sheet_date = _sheet_date_from_fecha(fecha)
    sheet_date_found, items = _find_sheet_date_with_data(db, sheet_date)
    if not sheet_date_found or not items:
        requested_str = sheet_date.strftime("%Y-%m-%d")
        raise HTTPException(
            status_code=404,
            detail=(
                f"Sin datos para {requested_str}. "
                "Pulse «Generar Excel desde Gmail» (Cargar datos > Generar Excel desde Gmail), espere a que termine y vuelva a descargar. "
                "Se procesan correos no leídos con adjuntos (imagen/PDF). Verifique que GEMINI_API_KEY esté configurado en el servidor."
            ),
        )
    sheet_date = sheet_date_found
    wb = Workbook()
    ws = wb.active
    ws.title = "Pagos"
    ws.append(["Asunto", "Fecha Pago", "Cedula", "Monto", "Referencia", "Link"])
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
