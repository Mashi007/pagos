"""
Endpoints para el pipeline Gmail -> Gemini -> BD (modulo Pagos).
Ejecucion manual: POST /pagos/gmail/run-now desde la UI (Pagos > Agregar pago > Generar Excel desde email).
Ejecucion automatica opcional: scheduler todos los dias cada hora :30 entre 06:30 y 19:30 (America/Caracas), filtro
pending_identification, si ENABLE_AUTOMATIC_SCHEDULED_JOBS y PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED en settings.
Manual y automatico comparten la misma regla de exclusion: no se inicia otra corrida si hay sync en estado running (ventana 2 h).
Criterio de listado Gmail: inbox + media (has:attachment o filename:imagen/PDF en cuerpo); adjuntos, incrustados o .eml rfc822 (deduplicado).
Solo si el remitente coincide con `clientes.email` o `email_secundario`: digitalizacion (Gemini), filas Excel/BD y comprobante en `pago_comprobante_imagen`; etiquetas MERCANTIL/BNC/BINANCE/BNV segun plantilla. Sin match (o error BD al consultar clientes): solo etiqueta ERROR EMAIL en Gmail, sin filas ni comprobante. Sin subidas a Google Drive.
Si ningun adjunto OK: no leido cuando hay candidatos imagen/PDF (estrellas no las toca el pipeline).
- POST /pagos/gmail/run-now: ejecutar pipeline ahora
- GET /pagos/gmail/download-excel y download-excel-temporal: descargar Excel (solo lectura; no borran BD); excluyen filas
  ya autoconciliadas por plantilla A–D (traza CUOTAS_OK / PAGO_SIN_CUOTAS con pago_id). `gmail_temporal` solo conserva pendientes de revisión.
  Query opcional plantilla A–D vs duplicado `pagos.numero_documento`.
- GET /pagos/gmail/status: ultima ejecucion; next_run_approx = proxima corrida programada Gmail si el scheduler tiene el job registrado
- GET /pagos/gmail/abcd-cuotas-traza: historial plantilla A–D → pago → cuotas (post-Gemini)
- GET /pagos/gmail/pipeline-eventos: eventos previos a fila sync (Gemini omitido, dedupe, etc.)
- POST /pagos/gmail/confirmar-dia: confirmacion si/no; si si, borrado de datos acumulados
"""
import io
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import and_, delete, desc, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem, GmailTemporal
from app.models.pagos_gmail_abcd_cuotas_traza import PagosGmailAbcdCuotasTraza
from app.models.pagos_gmail_pipeline_evento import PagosGmailPipelineEvento
from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials, log_pagos_gmail_config_status
from app.services.pagos_gmail.gmail_service import PAGOS_GMAIL_LABEL_ERROR_EMAIL
from app.services.pagos_gmail.helpers import format_monto_excel_pagos_gmail, formatear_cedula
from app.services.pagos_gmail.pipeline import run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


def _get_blocking_running_sync(db: Session) -> Optional[PagosGmailSync]:
    """
    Si hay una sync en estado running reciente (últimas 2 h), devuelve esa fila; si no, None.
    Ventana 2 h: evita doble ejecución mientras un pipeline legítimo corre; huérfanos por crash
    dejan de bloquear tras 2 h.
    """
    cutoff = datetime.utcnow() - timedelta(hours=2)
    return db.execute(
        select(PagosGmailSync).where(
            and_(
                PagosGmailSync.status == "running",
                PagosGmailSync.started_at >= cutoff,
            )
        ).limit(1)
    ).scalars().first()


def _is_pipeline_running(db: Session) -> bool:
    """True si hay una sync en estado running (misma ventana que _get_blocking_running_sync)."""
    return _get_blocking_running_sync(db) is not None


def _run_pipeline_background(sync_id: int, scan_filter: str = "all") -> None:
    """Ejecuta el pipeline en background con su propia sesion de BD. ón de BD (evita el timeout de 30s de Render/Axios)."""
    db = SessionLocal()
    logger.info("[PAGOS_GMAIL] [ETAPA] Inicio pipeline background sync_id=%s scan_filter=%s", sync_id, scan_filter)
    try:
        run_pipeline(db, existing_sync_id=sync_id, scan_filter=scan_filter)
    except Exception as e:
        logger.info("[PAGOS_GMAIL] [ETAPA] Pipeline finalizado sync_id=%s", sync_id)
        logger.exception("[PAGOS_GMAIL] [ETAPA] Error en background pipeline (sync_id=%s): %s", sync_id, e)
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


@router.get("/count-pending")
def count_pending(
    scan_filter: str = "all",
    db: Session = Depends(get_db),
):
    """
    Cuenta cuantos correos se procesarian sin iniciar el pipeline.
    El frontend puede mostrar "Se procesaran N correos. Iniciar? Si / No" y solo llamar
    POST /run-now si el usuario confirma (Si = inicia, No = no hace nada).
    scan_filter: "unread" | "read" | "all" | "pending_identification" | "error_email_rescan" (mismo que run-now; por defecto all).
    **all** / **pending_identification**: inbox + imagen/PDF, leídos y no leídos, cualquier etiqueta (incluye ERROR EMAIL).
    **unread** / **read**: mismo criterio base + solo no leídos / solo leídos en Gmail.
    """
    creds = get_pagos_gmail_credentials()
    if not creds:
        return {"count": 0, "scan_filter": scan_filter, "error": "no_credentials"}
    from app.services.pagos_gmail.gmail_service import build_gmail_service, count_messages_by_filter
    if scan_filter not in ("unread", "read", "all", "pending_identification", "error_email_rescan"):
        scan_filter = "all"
    try:
        gmail_svc = build_gmail_service(creds)
        count = count_messages_by_filter(gmail_svc, scan_filter)
        return {"count": count, "scan_filter": scan_filter}
    except Exception as e:
        logger.warning("[PAGOS_GMAIL] count-pending error: %s", e)
        return {"count": 0, "scan_filter": scan_filter, "error": str(e)[:200]}


@router.post("/run-now")
def run_now(
    background_tasks: BackgroundTasks,
    force: bool = True,
    scan_filter: str = "all",
    db: Session = Depends(get_db),
):
    """
    Inicia el pipeline en segundo plano (Gmail -> Gemini -> BD; comprobante en BD, .eml opcional en Drive) y devuelve inmediatamente.
    Solo correos con adjuntos; candidatos imagen/PDF: incrustados, adjuntos y reenvios rfc822.
    scan_filter: "unread" | "read" | "all" | "pending_identification" | "error_email_rescan" (por defecto all).
    Listado: por defecto inbox con imagen/PDF. Solo se digitalizan mensajes **sin etiquetas de usuario** Gmail, salvo modo **error_email_rescan** con **solo** la etiqueta ERROR EMAIL.
    **unread** / **read**: añade is:unread / is:read a la búsqueda.
    **error_email_rescan**: re-escaneo A/B; procesa si la unica etiqueta de usuario es ERROR EMAIL; otras etiquetas de usuario implican omitir.
    Listado completo por paginacion Gmail; procesamiento en orden bandeja (mas reciente primero, mas antiguo al final).
    Los mensajes no leidos quedan leidos al procesarlos en la corrida.
    El frontend debe hacer polling a GET /status hasta que last_status sea 'success' o 'error'.
    El parametro force se mantiene por compatibilidad y no aplica ninguna restriccion.
    """
    _ = force
    blocking = _get_blocking_running_sync(db)
    if blocking is not None:
        started = blocking.started_at.isoformat() if blocking.started_at else "?"
        raise HTTPException(
            status_code=409,
            detail=(
                f"Ya hay una sincronización en curso (sync_id={blocking.id}, iniciada={started}). "
                "Espere a que termine (consulte estado arriba) o, si quedó colgada más de 2 h, podrá iniciar otra. "
                "Borrar el acumulado (confirmar día) no detiene el proceso en segundo plano."
            ),
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
    # Validar scan_filter
    if scan_filter not in ("unread", "read", "all", "pending_identification", "error_email_rescan"):
        scan_filter = "all"
    # Lanzar pipeline en segundo plano; el cliente hace polling a /status
    background_tasks.add_task(_run_pipeline_background, sync_id, scan_filter)
    return {
        "sync_id": sync_id,
        "status": "running",
        "emails_processed": 0,
        "files_processed": 0,
    }


@router.get("/status")
def status(db: Session = Depends(get_db)):
    """Ultima ejecucion (manual o programada); next_run_approx solo si el escaneo Gmail programado esta registrado en el scheduler."""
    last = db.execute(select(PagosGmailSync).order_by(desc(PagosGmailSync.started_at)).limit(1)).scalars().first()
    latest_data_date = _get_latest_date_with_data(db)
    marcados = 0
    if last is not None:
        marcados = int(getattr(last, "correos_marcados_revision", 0) or 0)
    run_summary = getattr(last, "run_summary", None) if last is not None else None
    next_run_approx: Optional[str] = None
    try:
        from app.core.scheduler import get_pagos_gmail_scan_next_run_iso

        next_run_approx = get_pagos_gmail_scan_next_run_iso()
    except Exception:
        logger.debug("No se pudo obtener next_run_approx del scheduler Gmail", exc_info=True)
    return {
        "last_run": last.started_at.isoformat() if last and last.started_at else None,
        "last_status": last.status if last else None,
        "last_emails": last.emails_processed if last else 0,
        "last_files": last.files_processed if last else 0,
        "last_error": last.error_message if last and last.status == "error" else None,
        "next_run_approx": next_run_approx,
        "latest_data_date": latest_data_date,
        "last_correos_marcados_revision": marcados,
        "last_run_summary": run_summary,
    }


@router.get("/abcd-cuotas-traza")
def list_abcd_cuotas_traza(
    limit: int = Query(100, ge=1, le=500),
    sync_id: Optional[int] = Query(None, ge=1),
    etapa_final: Optional[str] = Query(
        None,
        description="Filtrar por etapa: CUOTAS_OK, PAGO_SIN_CUOTAS, OMITIDO_DUPLICADO, OMITIDO_NEGOCIO, ERROR_PIPELINE",
    ),
    db: Session = Depends(get_db),
):
    """
    Historial de intentos **plantilla banco A–D** después del escaneo Gmail/Gemini: si el pago llegó a
    `pagos`, cuántas cuotas se tocaron y el código de resultado.

    **Cómo interpretar `etapa_final`:**
    - **CUOTAS_OK**: se creó `pago` y la cascada aplicó al menos una operación a cuotas (`cuotas_completadas` + `cuotas_parciales` > 0).
    - **PAGO_SIN_CUOTAS**: `pago` creado pero ninguna cuota recibió monto (revisar préstamo / cuotas pendientes).
    - **OMITIDO_DUPLICADO**: serial ya existía en `pagos` / `pagos_con_errores`; no se duplicó el pago.
    - **OMITIDO_NEGOCIO**: validación o regla de negocio (ver `motivo` / `detalle`: varios préstamos, huella, etc.).
    - **OMITIDO_SIN_MONTO_OPERACION**: plantilla NR sin `monto_operacion` legible (Gemini NA); queda revisión manual / Excel.
    - **ERROR_PIPELINE**: excepción al evaluar o procesar (ver `detalle`).
    """
    q = select(PagosGmailAbcdCuotasTraza).order_by(desc(PagosGmailAbcdCuotasTraza.created_at)).limit(limit)
    if sync_id is not None:
        q = q.where(PagosGmailAbcdCuotasTraza.sync_id == sync_id)
    if etapa_final and etapa_final.strip():
        q = q.where(PagosGmailAbcdCuotasTraza.etapa_final == etapa_final.strip()[:40])
    try:
        rows = db.execute(q).scalars().all()
    except Exception as e:
        logger.warning("[PAGOS_GMAIL] abcd-cuotas-traza lectura: %s", e)
        raise HTTPException(
            status_code=503,
            detail="No se pudo leer la traza (¿migración 059 aplicada?). Ejecute alembic upgrade.",
        ) from e

    sync_item_ids = [int(x.sync_item_id) for x in rows if x.sync_item_id is not None]
    si_map: dict[int, PagosGmailSyncItem] = {}
    if sync_item_ids:
        uniq = list(dict.fromkeys(sync_item_ids))
        for si in db.execute(
            select(PagosGmailSyncItem).where(PagosGmailSyncItem.id.in_(uniq))
        ).scalars().all():
            si_map[int(si.id)] = si

    items = []
    for r in rows:
        si_row = si_map.get(int(r.sync_item_id)) if r.sync_item_id is not None else None
        items.append(
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "sync_id": r.sync_id,
                "sync_item_id": r.sync_item_id,
                "gmail_message_id": getattr(si_row, "gmail_message_id", None)
                if si_row
                else None,
                "gmail_thread_id": getattr(si_row, "gmail_thread_id", None)
                if si_row
                else None,
                "plantilla_fmt": r.plantilla_fmt,
                "cedula": r.cedula,
                "numero_referencia": r.numero_referencia,
                "banco_excel": r.banco_excel,
                "archivo_adjunto": r.archivo_adjunto,
                "comprobante_imagen_id": r.comprobante_imagen_id,
                "duplicado_documento": bool(r.duplicado_documento),
                "etapa_final": r.etapa_final,
                "motivo": r.motivo,
                "detalle": r.detalle,
                "pago_id": r.pago_id,
                "prestamo_id": r.prestamo_id,
                "cuotas_completadas": int(r.cuotas_completadas or 0),
                "cuotas_parciales": int(r.cuotas_parciales or 0),
                "conciliado_final": r.conciliado_final,
                "pago_estado_final": r.pago_estado_final,
            }
        )
    return {"total": len(items), "items": items}


@router.get("/pipeline-eventos")
def list_pipeline_eventos(
    limit: int = Query(200, ge=1, le=2000),
    sync_id: Optional[int] = Query(None, ge=1),
    motivo: Optional[str] = Query(
        None,
        description="Filtrar por motivo (ej. NO_PLANTILLA_GEMINI, DEDUPE_SHA_CORRIDA).",
    ),
    db: Session = Depends(get_db),
):
    """
    Auditoría de pasos **antes** de crear fila en `pagos_gmail_sync_item` (rechazo plantilla, dedupe SHA en corrida, etc.).
    Requiere migración **064**. Útil para enlazar con Gmail por `gmail_message_id` / `gmail_thread_id`.
    """
    q = select(PagosGmailPipelineEvento).order_by(desc(PagosGmailPipelineEvento.created_at)).limit(limit)
    if sync_id is not None:
        q = q.where(PagosGmailPipelineEvento.sync_id == sync_id)
    if motivo and motivo.strip():
        q = q.where(PagosGmailPipelineEvento.motivo == motivo.strip()[:64])
    try:
        rows = db.execute(q).scalars().all()
    except Exception as e:
        logger.warning("[PAGOS_GMAIL] pipeline-eventos lectura: %s", e)
        raise HTTPException(
            status_code=503,
            detail="No se pudo leer eventos (¿migración 064 aplicada?). Ejecute alembic upgrade head.",
        ) from e
    out = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "sync_id": r.sync_id,
                "gmail_message_id": r.gmail_message_id,
                "gmail_thread_id": r.gmail_thread_id,
                "sha256_hex": r.sha256_hex,
                "filename": r.filename,
                "motivo": r.motivo,
                "detalle": r.detalle,
            }
        )
    return {"total": len(out), "items": out}


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
    Confirmación desde la interfaz (sí/no).
    - Sin fecha: borra TODOS los ítems (limpiar el acumulado completo tras exportar).
    - Con fecha específica: borra solo los ítems de esa fecha (sheet_name exacto).
    Si confirmado=false no se hace nada.
    """
    if not body.confirmado:
        return {"confirmado": False, "mensaje": "Sin cambios. Los datos del día se mantienen."}
    if body.fecha and body.fecha.strip():
        from app.services.pagos_gmail.helpers import get_sheet_name_for_date
        sheet_date = _sheet_date_from_fecha(body.fecha)
        sheet_name = get_sheet_name_for_date(sheet_date)
        result = db.execute(delete(PagosGmailSyncItem).where(PagosGmailSyncItem.sheet_name == sheet_name))
        db.commit()
        deleted = result.rowcount if hasattr(result, "rowcount") else 0
        logger.info("Pagos Gmail confirmar-dia: borrados %d ítems de sheet_name=%s", deleted, sheet_name)
        run = _get_blocking_running_sync(db)
        if run is not None:
            logger.warning(
                "Pagos Gmail confirmar-dia: datos de fecha borrados pero sigue sync en running "
                "(sync_id=%s iniciada=%s). run-now puede devolver 409 hasta que termine o pasen 2 h.",
                run.id,
                run.started_at.isoformat() if run.started_at else "?",
            )
        return {
            "confirmado": True,
            "borrados": deleted,
            "mensaje": f"Datos de {sheet_date.strftime('%Y-%m-%d')} borrados ({deleted} filas)." if deleted else f"No había datos para {sheet_date.strftime('%Y-%m-%d')}.",
            "pipeline_running": run is not None,
            "blocking_sync_id": run.id if run is not None else None,
        }
    else:
        # Sin fecha: borrar todo el acumulado
        result = db.execute(delete(PagosGmailSyncItem))
        db.execute(delete(GmailTemporal))
        db.commit()
        deleted = result.rowcount if hasattr(result, "rowcount") else 0
        logger.info("Pagos Gmail confirmar-dia: borrados TODOS los ítems (%d)", deleted)
        run = _get_blocking_running_sync(db)
        if run is not None:
            logger.warning(
                "Pagos Gmail confirmar-dia: acumulado borrado pero sigue sync en running "
                "(sync_id=%s iniciada=%s). run-now devolverá 409 hasta que termine o pasen 2 h.",
                run.id,
                run.started_at.isoformat() if run.started_at else "?",
            )
        return {
            "confirmado": True,
            "borrados": deleted,
            "mensaje": f"Acumulado completo borrado ({deleted} filas). Listo para el próximo ciclo.",
            "pipeline_running": run is not None,
            "blocking_sync_id": run.id if run is not None else None,
        }


def _find_most_recent_data(db: Session) -> tuple[Optional[str], Optional[datetime], list]:
    """
    Devuelve los ítems más recientes (acumulado), ordenados por fecha de creación ascendente.
    Por defecto incluye toda la bandeja (hasta 500k items). Opcional: PAGOS_GMAIL_DOWNLOAD_EXCEL_MAX_ITEMS.
    Devuelve (sheet_name_ref, email_date_ref, items) o (None, None, []).
    """
    from app.core.config import settings
    from app.services.pagos_gmail.helpers import parse_date_from_sheet_name
    max_items = getattr(settings, "PAGOS_GMAIL_DOWNLOAD_EXCEL_MAX_ITEMS", 0) or 0
    if max_items <= 0:
        max_items = 500000  # toda la bandeja en un solo archivo
    logger.info("[PAGOS_GMAIL] [ETAPA] _find_most_recent_data max_items=%s", max_items)
    rows = db.execute(
        select(PagosGmailSyncItem)
        .order_by(desc(PagosGmailSyncItem.created_at))
        .limit(max_items)
    ).scalars().all()
    items = list(reversed(rows))
    logger.info("[PAGOS_GMAIL] [ETAPA] _find_most_recent_data items_en_bd=%s devueltos=%s", len(rows), len(items))  # más recientes primero en el límite, pero orden ascendente en Excel
    if not items:
        return None, None, []
    last_sheet_name = items[-1].sheet_name or ""
    email_date = parse_date_from_sheet_name(last_sheet_name)
    return last_sheet_name, email_date, items


def _find_sheet_by_fecha(db: Session, fecha_date: datetime) -> tuple[Optional[str], list]:
    """Busca items para una fecha concreta (sheet_name exacto). Devuelve (sheet_name, items)."""
    from app.services.pagos_gmail.helpers import get_sheet_name_for_date
    sheet_name = get_sheet_name_for_date(fecha_date)
    items = db.execute(
        select(PagosGmailSyncItem)
        .where(PagosGmailSyncItem.sheet_name == sheet_name)
        .order_by(PagosGmailSyncItem.created_at)
    ).scalars().all()
    return (sheet_name, list(items)) if items else (sheet_name, [])


def _excluir_filas_cedula_error_email(items: list) -> list:
    """La columna cédula 'ERROR EMAIL' no debe aparecer en Excel ni contarse como dato exportable."""
    return [
        it
        for it in items
        if (getattr(it, "cedula", None) or "").strip() != PAGOS_GMAIL_LABEL_ERROR_EMAIL
    ]


def _excluir_sync_items_alta_gmail_abcd_automatica_ok(db: Session, items: list) -> list:
    """
    Ítems de sync cuyo comprobante A–D pasó validadores y generó `pago` (traza CUOTAS_OK o PAGO_SIN_CUOTAS):
    no deben repetirse en Excel de revisión (el pago ya está en `pagos`).
    """
    ids: list[int] = []
    for it in items:
        raw = getattr(it, "id", None)
        if raw is None:
            continue
        try:
            ids.append(int(raw))
        except (TypeError, ValueError):
            continue
    if not ids:
        return items
    rows = (
        db.execute(
            select(PagosGmailAbcdCuotasTraza.sync_item_id).where(
                PagosGmailAbcdCuotasTraza.sync_item_id.in_(ids),
                PagosGmailAbcdCuotasTraza.etapa_final.in_(("CUOTAS_OK", "PAGO_SIN_CUOTAS")),
                PagosGmailAbcdCuotasTraza.pago_id.isnot(None),
            )
        )
        .scalars()
        .all()
    )
    excl = {int(x) for x in rows if x is not None}
    if not excl:
        return items
    return [it for it in items if int(getattr(it, "id", 0) or 0) not in excl]


def _filtrar_items_excel_duplicado_documento_abcd(
    db: Session,
    items: list,
    *,
    solo_duplicados_documento: bool,
    excluir_duplicados_documento: bool,
) -> list:
    """
    Plantilla banco A–D (columna `banco`): filtra por serial ya presente en `pagos` /
    `pagos_con_errores` (misma normalización que alta de pagos). Ver `plantilla_abcd_proceso_negocio`.
    """
    from app.services.pagos_gmail.plantilla_abcd_proceso_negocio import (
        item_sync_abcd_candidato_revision_duplicado,
    )

    if solo_duplicados_documento:
        return [
            it
            for it in items
            if item_sync_abcd_candidato_revision_duplicado(
                banco_excel=getattr(it, "banco", None),
                referencia=getattr(it, "numero_referencia", None),
                db=db,
            )
        ]
    if excluir_duplicados_documento:
        return [
            it
            for it in items
            if not item_sync_abcd_candidato_revision_duplicado(
                banco_excel=getattr(it, "banco", None),
                referencia=getattr(it, "numero_referencia", None),
                db=db,
            )
        ]
    return items


def _get_latest_date_with_data(db: Session) -> Optional[str]:
    """Devuelve la fecha del correo (YYYY-MM-DD) del ítem más reciente en BD, para guiar al usuario."""
    from app.services.pagos_gmail.helpers import parse_date_from_sheet_name
    row = db.execute(
        select(PagosGmailSyncItem.sheet_name)
        .order_by(desc(PagosGmailSyncItem.created_at))
        .limit(1)
    ).scalars().first()
    if not row:
        return None
    d = parse_date_from_sheet_name(row)
    return d.strftime("%Y-%m-%d") if d else None


@router.get("/download-excel")
def download_excel(
    fecha: Optional[str] = None,
    solo_duplicados_documento: bool = Query(
        False,
        description="Solo filas banco plantilla A–D cuyo serial ya existe en pagos o pagos_con_errores (revisión manual).",
    ),
    excluir_duplicados_documento: bool = Query(
        False,
        description="Excluye esas filas duplicadas; el resto (incl. NR y no-ABCD) sigue en el Excel.",
    ),
    db: Session = Depends(get_db),
):
    """
    Genera y devuelve un Excel con los ítems procesados (solo lectura en BD).
    No borra ni modifica filas: el acumulado sigue en el servidor para siguientes descargas y nuevos procesamientos.
    - Sin ?fecha: descarga el lote más reciente en BD, sin importar la fecha del correo
      (cubre backlog de cualquier antigüedad; los correos se procesan mientras estén no leídos).
    - Con ?fecha=YYYY-MM-DD: descarga exactamente esa fecha.
    Si no hay datos devuelve 404 (no se genera Excel vacío).
    Columnas: Banco, Cedula, Fecha, Monto, Serial documento, Correo Pagador.
    No incluye filas cuya cédula sea la literal **ERROR EMAIL** (reservada para fallo de remitente en clientes).
    No incluye comprobantes plantilla A–D ya dados de alta automáticamente (conciliados y con traza de éxito en BD).
    Filtros opcionales (plantilla banco A–D, columna Banco): `solo_duplicados_documento`, `excluir_duplicados_documento`
    (no usar ambos a la vez).
    Para vaciar tablas usar POST /pagos/gmail/confirmar-dia con confirmado=true.
    """
    from openpyxl import Workbook
    items: list = []
    sheet_date: Optional[datetime] = None
    if solo_duplicados_documento and excluir_duplicados_documento:
        raise HTTPException(
            status_code=400,
            detail="No combine solo_duplicados_documento y excluir_duplicados_documento en la misma petición.",
        )
    logger.info("[PAGOS_GMAIL] [ETAPA] download-excel inicio fecha=%s", fecha or "(sin fecha = toda la bandeja)")

    if fecha and fecha.strip():
        # Fecha explícita: buscar ese día concreto
        fecha_date = _sheet_date_from_fecha(fecha)
        _, items = _find_sheet_by_fecha(db, fecha_date)
        logger.info("[PAGOS_GMAIL] [ETAPA] download-excel por fecha items=%s", len(items))
        sheet_date = fecha_date
    else:
        # Sin fecha: lote más reciente en BD (backlog de cualquier antigüedad)
        logger.info("[PAGOS_GMAIL] [ETAPA] download-excel sin fecha items=%s", len(items))
        _, sheet_date, items = _find_most_recent_data(db)

    items = _excluir_filas_cedula_error_email(items)
    items = _excluir_sync_items_alta_gmail_abcd_automatica_ok(db, items)
    items = _filtrar_items_excel_duplicado_documento_abcd(
        db,
        items,
        solo_duplicados_documento=solo_duplicados_documento,
        excluir_duplicados_documento=excluir_duplicados_documento,
    )
    if not items:
        raise HTTPException(
            status_code=404,
            detail=(
                "Sin datos disponibles. "
                "Si todo fue autoconciliado (plantilla A–D con validadores OK), no quedan filas para Excel. "
                "Pulse «Generar Excel desde Gmail» para procesar correos no leídos con adjuntos (imagen/PDF) "
                "y vuelva a descargar. Verifique que GEMINI_API_KEY esté configurado en el servidor."
                + (f" (buscado: {fecha})" if fecha else "")
                + (
                    " Si usó filtros de duplicado por documento (plantilla A–D), pruebe sin ellos."
                    if (solo_duplicados_documento or excluir_duplicados_documento)
                    else ""
                )
            ),
        )

    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Pagos"
        ws.append(
            [
                "Banco",
                "Cedula",
                "Fecha",
                "Monto",
                "Serial documento",
                "Correo Pagador",
                "Gmail message id",
                "Gmail thread id",
            ]
        )
        for it in items:  # fila 1 = cabecera
            ws.append(
                [
                    it.banco or "",
                    formatear_cedula(it.cedula or ""),
                    it.fecha_pago or "",
                    format_monto_excel_pagos_gmail(it.monto) or (it.monto or ""),
                    it.numero_referencia or "",
                    it.correo_origen or "",
                    getattr(it, "gmail_message_id", None) or "",
                    getattr(it, "gmail_thread_id", None) or "",
                ]
            )
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
    except Exception as e:
        logger.exception("[PAGOS_GMAIL] Error generando Excel: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Error al generar el archivo Excel. Intente de nuevo o contacte soporte.",
        ) from e

    date_str = sheet_date.strftime("%Y-%m-%d") if sheet_date else "sin-fecha"
    filename = f"Pagos_Gmail_{date_str}.xlsx"
    logger.info("[PAGOS_GMAIL] [ETAPA] download-excel OK filas=%s filename=%s", len(items), filename)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )



@router.get("/download-excel-temporal")
def download_excel_temporal(
    solo_duplicados_documento: bool = Query(
        False,
        description="Solo filas banco plantilla A–D cuyo serial ya existe en pagos o pagos_con_errores (revisión manual).",
    ),
    excluir_duplicados_documento: bool = Query(
        False,
        description="Excluye esas filas duplicadas; el resto sigue en el Excel.",
    ),
    db: Session = Depends(get_db),
):
    """
    Genera Excel desde la tabla temporal gmail_temporal: solo filas que siguieron en tabla tras el pipeline
    (NR, duplicados, A–D que no pasaron validadores de negocio, etc.). Las filas A–D autoconciliadas se eliminan
    de `gmail_temporal` al cerrar el alta en `pagos`.
    Excluye filas con cédula **ERROR EMAIL** (no deben exportarse).
    Filtros opcionales (misma semántica que download-excel): `solo_duplicados_documento`, `excluir_duplicados_documento`.
    NO vacia la tabla: los datos solo se borran al usar el boton "Vaciar tabla (Generar Excel desde Gmail)". Si no hay datos devuelve 404.
    """
    from openpyxl import Workbook

    if solo_duplicados_documento and excluir_duplicados_documento:
        raise HTTPException(
            status_code=400,
            detail="No combine solo_duplicados_documento y excluir_duplicados_documento en la misma petición.",
        )

    items = db.execute(
        select(GmailTemporal).order_by(GmailTemporal.created_at)
    ).scalars().all()
    items = _excluir_filas_cedula_error_email(list(items))
    items = _filtrar_items_excel_duplicado_documento_abcd(
        db,
        items,
        solo_duplicados_documento=solo_duplicados_documento,
        excluir_duplicados_documento=excluir_duplicados_documento,
    )
    if not items:
        raise HTTPException(
            status_code=404,
            detail=(
                "Sin datos en tabla temporal (o todo fue autoconciliado y ya no quedan filas pendientes). "
                "Procese correos Gmail primero; los comprobantes A–D válidos pasan a `pagos` y se omiten del Excel."
                + (
                    " Si usó filtros de duplicado por documento, pruebe sin ellos."
                    if (solo_duplicados_documento or excluir_duplicados_documento)
                    else ""
                )
            ),
        )
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Pagos"
        ws.append(
            [
                "Banco",
                "Cedula",
                "Fecha",
                "Monto",
                "Serial documento",
                "Correo Pagador",
                "Gmail message id",
                "Gmail thread id",
            ]
        )
        for it in items:
            ws.append(
                [
                    it.banco or "",
                    formatear_cedula(it.cedula or ""),
                    it.fecha_pago or "",
                    format_monto_excel_pagos_gmail(it.monto) or (it.monto or ""),
                    it.numero_referencia or "",
                    it.correo_origen or "",
                    getattr(it, "gmail_message_id", None) or "",
                    getattr(it, "gmail_thread_id", None) or "",
                ]
            )
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
    except Exception as e:
        logger.exception("[PAGOS_GMAIL] Error generando Excel temporal: %s", e)
        raise HTTPException(status_code=500, detail="Error al generar Excel.") from e

    # No se vacia la BD aqui: solo el boton Vaciar tabla puede borrar.
    from datetime import datetime as dt
    date_str = dt.utcnow().strftime("%Y-%m-%d")
    filename = f"Pagos_Gmail_temporal_{date_str}.xlsx"
    logger.info("[PAGOS_GMAIL] download-excel-temporal OK filas=%s (tabla no se vacia)", len(items))
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

@router.get("/diagnostico")
def diagnostico(db: Session = Depends(get_db)):
    """
    Diagnóstico integral del pipeline: verifica credenciales, Gmail, Drive, Sheets y Gemini
    con 1 correo real. Devuelve JSON detallado con el resultado de cada paso.
    """
    from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
    from app.services.pagos_gmail.gmail_service import (
        build_gmail_service,
        list_messages_by_filter,
        get_message_full_payload,
        get_pagos_gmail_image_pdf_files_for_pipeline,
    )
    from app.services.pagos_gmail.drive_service import build_drive_service
    from app.services.pagos_gmail.gemini_service import (
        classify_and_extract_pagos_gmail_attachment,
        check_gemini_available,
    )
    from app.services.pagos_gmail.pdf_pages import expand_pipeline_pdf_tuples
    from app.core.config import settings
    import traceback

    result: dict = {
        "paso_1_credenciales": None,
        "paso_2_gmail_list": None,
        "paso_3_primer_correo": None,
        "paso_4_imagenes": None,
        "paso_5_gemini_health": None,
        "paso_6_gemini_extraccion": None,
        "config": {
            "GEMINI_API_KEY_set": bool(getattr(settings, "GEMINI_API_KEY", None)),
            "GEMINI_MODEL": getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash"),
        }
    }

    # PASO 1: Credenciales
    try:
        creds = get_pagos_gmail_credentials()
        if creds:
            result["paso_1_credenciales"] = {"ok": True, "tipo": str(type(creds).__name__)}
        else:
            result["paso_1_credenciales"] = {"ok": False, "error": "get_pagos_gmail_credentials() devolvió None"}
            return result
    except Exception as e:
        result["paso_1_credenciales"] = {"ok": False, "error": str(e), "trace": traceback.format_exc()[-500:]}
        return result

    # PASO 2: Listar inbox + media (mismo criterio que el pipeline; leídos y no leídos)
    try:
        gmail_svc = build_gmail_service(creds)
        messages = list_messages_by_filter(gmail_svc, "unread")
        result["paso_2_gmail_list"] = {
            "ok": True,
            "total_en_inbox_media": len(messages),
            "primeros_3": [
                {"id": m["id"], "from": m["headers"].get("from", "")[:60],
                 "subject": m["headers"].get("subject", "")[:60]}
                for m in messages[:3]
            ]
        }
        if not messages:
            result["paso_2_gmail_list"]["advertencia"] = (
                "No hay mensajes en inbox que cumplan criterio imagen/PDF (listado incluye leídos y no leídos)"
            )
            return result
    except Exception as e:
        result["paso_2_gmail_list"] = {"ok": False, "error": str(e), "trace": traceback.format_exc()[-500:]}
        return result

    # PASO 3: Primer correo — payload completo
    try:
        msg = messages[0]
        full_payload = get_message_full_payload(gmail_svc, msg["id"])
        mime_top = full_payload.get("mimeType", "desconocido") if full_payload else "payload vacío"
        parts_top = [p.get("mimeType", "?") for p in (full_payload or {}).get("parts", [])]
        result["paso_3_primer_correo"] = {
            "ok": True,
            "msg_id": msg["id"],
            "from": msg["headers"].get("from", "")[:80],
            "subject": msg["headers"].get("subject", "")[:80],
            "mimeType_top": mime_top,
            "parts_top_level": parts_top,
        }
    except Exception as e:
        result["paso_3_primer_correo"] = {"ok": False, "error": str(e), "trace": traceback.format_exc()[-500:]}
        return result

    # PASO 4: Extracción de imágenes del primer correo
    candidatos = []
    try:
        attachments = get_pagos_gmail_image_pdf_files_for_pipeline(
            gmail_svc, msg["id"], full_payload
        )
        candidatos = expand_pipeline_pdf_tuples(attachments)
        result["paso_4_imagenes"] = {
            "ok": True,
            "nota": "Cuerpo incrustado + adjuntos imagen/PDF + message/rfc822 (.eml), deduplicado por contenido; PDF multi-pagina expandido a N candidatos",
            "total_imagenes": len(candidatos),
            "detalle": [
                {"nombre": f, "bytes": len(c), "mime": m, "origen": o}
                for f, c, m, o in candidatos[:5]
            ]
        }
    except Exception as e:
        result["paso_4_imagenes"] = {"ok": False, "error": str(e), "trace": traceback.format_exc()[-500:]}
        return result

    # PASO 5: Health check de Gemini (prompt de texto simple)
    try:
        gemini_health = check_gemini_available()
        result["paso_5_gemini_health"] = gemini_health
    except Exception as e:
        result["paso_5_gemini_health"] = {"ok": False, "error": str(e)}

    # PASO 6: Extracción real con Gemini sobre la primera imagen (si existe)
    if candidatos:
        fname, content, mime, origen = candidatos[0]
        try:
            from_hdr = (msg.get("headers") or {}).get("from") or ""
            fmt, data = classify_and_extract_pagos_gmail_attachment(
                content,
                fname,
                remitente_correo_header=from_hdr,
                origen_binario=origen,
            )
            result["paso_6_gemini_extraccion"] = {
                "ok": True,
                "archivo": fname,
                "bytes": len(content),
                "mime": mime,
                "origen": origen,
                "formato": fmt,
                "resultado": data,
            }
        except Exception as e:
            result["paso_6_gemini_extraccion"] = {
                "ok": False,
                "archivo": fname,
                "bytes": len(content),
                "error": str(e),
                "trace": traceback.format_exc()[-500:],
            }
    else:
        result["paso_6_gemini_extraccion"] = {
            "ok": False,
            "motivo": "Sin imágenes >= 10KB en el primer correo — Gemini no fue llamado",
        }

    return result
