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
    # 5 min: si el pipeline no termina en 5 min (SIGTERM/crash), se considera huérfano
    cutoff = datetime.utcnow() - timedelta(minutes=5)
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
        "last_error": last.error_message if last and last.status == "error" else None,
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


def _find_most_recent_data(db: Session) -> tuple[Optional[str], Optional[datetime], list]:
    """
    Devuelve TODOS los ítems del sync más reciente que tiene ítems (independientemente de la fecha
    del correo). Así el usuario descarga exactamente lo que se procesó en el último run, aunque
    los correos sean de fechas distintas o de semanas atrás.
    Devuelve (sheet_name_ref, email_date_ref, items) o (None, None, []).
    sheet_name_ref y email_date_ref son del ítem más reciente del sync (solo para nombrar el archivo).
    """
    from app.services.pagos_gmail.helpers import parse_date_from_sheet_name
    # Sync más reciente que tiene ítems
    sync_row = db.execute(
        select(PagosGmailSync)
        .where(PagosGmailSync.files_processed > 0)
        .order_by(desc(PagosGmailSync.started_at))
        .limit(1)
    ).scalars().first()
    if not sync_row:
        # Fallback: buscar cualquier ítem aunque files_processed sea 0
        sync_row = db.execute(
            select(PagosGmailSync)
            .join(PagosGmailSyncItem, PagosGmailSyncItem.sync_id == PagosGmailSync.id)
            .order_by(desc(PagosGmailSync.started_at))
            .limit(1)
        ).scalars().first()
    if not sync_row:
        return None, None, []
    items = db.execute(
        select(PagosGmailSyncItem)
        .where(PagosGmailSyncItem.sync_id == sync_row.id)
        .order_by(PagosGmailSyncItem.created_at)
    ).scalars().all()
    if not items:
        return None, None, []
    # Fecha del primer ítem del sync (para nombre del archivo)
    first_sheet_name = items[0].sheet_name or ""
    email_date = parse_date_from_sheet_name(first_sheet_name)
    return first_sheet_name, email_date, list(items)


def _find_sheet_by_fecha(db: Session, fecha_date: datetime) -> tuple[Optional[str], list]:
    """Busca items para una fecha concreta (sheet_name exacto). Devuelve (sheet_name, items)."""
    from app.services.pagos_gmail.helpers import get_sheet_name_for_date
    sheet_name = get_sheet_name_for_date(fecha_date)
    items = db.execute(
        select(PagosGmailSyncItem)
        .join(PagosGmailSync, PagosGmailSyncItem.sync_id == PagosGmailSync.id)
        .where(PagosGmailSyncItem.sheet_name == sheet_name)
        .order_by(PagosGmailSyncItem.created_at)
    ).scalars().all()
    return (sheet_name, list(items)) if items else (sheet_name, [])


def _get_latest_date_with_data(db: Session) -> Optional[str]:
    """Devuelve la fecha del correo (YYYY-MM-DD) del ítem más reciente en BD, para guiar al usuario."""
    from app.services.pagos_gmail.helpers import parse_date_from_sheet_name
    row = db.execute(
        select(PagosGmailSyncItem.sheet_name)
        .join(PagosGmailSync, PagosGmailSyncItem.sync_id == PagosGmailSync.id)
        .order_by(desc(PagosGmailSyncItem.created_at))
        .limit(1)
    ).scalars().first()
    if not row:
        return None
    d = parse_date_from_sheet_name(row)
    return d.strftime("%Y-%m-%d") if d else None


@router.get("/download-excel")
def download_excel(fecha: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Genera y devuelve un Excel con los ítems procesados.
    - Sin ?fecha: descarga el lote más reciente en BD, sin importar la fecha del correo
      (cubre backlog de cualquier antigüedad; los correos se procesan mientras estén no leídos).
    - Con ?fecha=YYYY-MM-DD: descarga exactamente esa fecha.
    Si no hay datos devuelve 404 (no se genera Excel vacío).
    Columnas: Asunto, Fecha Pago, Cédula, Monto, Referencia, Link.
    """
    from openpyxl import Workbook
    items: list = []
    sheet_date: Optional[datetime] = None

    if fecha and fecha.strip():
        # Fecha explícita: buscar ese día concreto
        fecha_date = _sheet_date_from_fecha(fecha)
        _, items = _find_sheet_by_fecha(db, fecha_date)
        sheet_date = fecha_date
    else:
        # Sin fecha: lote más reciente en BD (backlog de cualquier antigüedad)
        _, sheet_date, items = _find_most_recent_data(db)

    if not items:
        raise HTTPException(
            status_code=404,
            detail=(
                "Sin datos disponibles. "
                "Pulse «Generar Excel desde Gmail» para procesar correos no leídos con adjuntos (imagen/PDF) "
                "y vuelva a descargar. Verifique que GEMINI_API_KEY esté configurado en el servidor."
                + (f" (buscado: {fecha})" if fecha else "")
            ),
        )

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
    date_str = sheet_date.strftime("%Y-%m-%d") if sheet_date else "sin-fecha"
    filename = f"Pagos_Gmail_{date_str}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
