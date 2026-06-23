"""
Endpoints para el pipeline Gmail -> Gemini -> BD (modulo Pagos).
Ejecucion manual: POST /pagos/gmail/run-now desde la UI (Pagos > Agregar pago > Correos Gmail).
Ejecucion automatica opcional: scheduler todos los dias cada hora :30 entre 06:30 y 19:30 (America/Caracas), filtro
pending_identification, si ENABLE_AUTOMATIC_SCHEDULED_JOBS y PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED en settings.
Manual y automatico comparten la misma regla de exclusion: no se inicia otra corrida si hay sync en estado running (ventana 2 h).
Criterio de listado Gmail: inbox + media (has:attachment o filename:imagen/PDF en cuerpo); adjuntos, incrustados o .eml rfc822.
Clasificación vigente: etiqueta final única por correo con precedencia Paso 1 (A/B), Paso 2 (C/D con remitente en clientes), Plan B fuera de BD (A/B/C) y fallback TEXTO->ERROR EMAIL->MANUAL.
Si el mensaje ya tiene cualquier etiqueta de usuario Gmail, se omite (skip total) para evitar reetiquetar.
- POST /pagos/gmail/run-now: ejecutar pipeline ahora
- GET /pagos/gmail/download-excel* (descontinuado, 410): usar Pagos y Pagos con errores tras run-now.
- POST /pagos/gmail/migrar-pendientes-a-con-errores: mueve `gmail_temporal` a revisión en app.
- GET /pagos/gmail/status: ultima ejecucion; next_run_approx = proxima corrida programada Gmail si el scheduler tiene el job registrado
- GET /pagos/gmail/abcd-cuotas-traza: historial plantilla A–D → pago → cuotas (post-Gemini)
- GET /pagos/gmail/pipeline-eventos: eventos previos a fila sync (Gemini omitido, remitente inválido, etc.)
- POST /pagos/gmail/confirmar-dia: confirmacion si/no; si si, borrado de datos acumulados
"""
import io
import logging
import re
from datetime import datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import and_, delete, desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.deps import get_current_user
from app.core.documento import compose_numero_documento_almacenado, normalize_documento
from app.models.cliente import Cliente
from app.models.pago_con_error import PagoConError
from app.models.pagos_gmail_sync import PagosGmailSync, PagosGmailSyncItem, GmailTemporal
from app.models.pagos_gmail_abcd_cuotas_traza import PagosGmailAbcdCuotasTraza
from app.models.pagos_gmail_pipeline_evento import PagosGmailPipelineEvento
from app.models.prestamo import Prestamo
from app.services.pago_numero_documento import numero_documento_ya_registrado
from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials, log_pagos_gmail_config_status
from app.services.pagos_gmail.gmail_service import (
    PAGOS_GMAIL_LABEL_ERROR_EMAIL,
    PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER,
    extract_lote_it_master_cedula_from_subject,
)
from app.services.pagos_gmail.helpers import format_monto_excel_pagos_gmail, formatear_cedula
from app.services.pagos_gmail.pipeline import run_pipeline
from app.services.pagos_gmail.sync_stale import (
    get_blocking_running_gmail_sync,
    gmail_sync_looks_stale,
    reconcile_blocking_running_gmail_sync_if_stale,
    reconcile_stale_running_gmail_sync,
)
from app.services.pagos_gmail.plantilla_abcd_proceso_negocio import (
    PAGOS_GMAIL_UMBRAL_REVISION_MANUAL_USD,
    monto_gmail_sync_requiere_revision_manual_usd,
)
from app.utils.cedula_almacenamiento import resolver_cedula_almacenada_en_clientes

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])

# Ruta canónica del comprobante en BD (cabecera pagos_con_errores.documento_ruta VARCHAR 255).
_COMPROBANTE_IMAGEN_PATH_RE = re.compile(
    r"(/api/v1/pagos/comprobante-imagen/[0-9a-fA-F]{32})\b",
    re.IGNORECASE,
)


def _documento_ruta_desde_gmail_temporal(drive_link: Optional[str]) -> Optional[str]:
    """
    Persistir enlace al comprobante al pasar gmail_temporal -> pagos_con_errores.
    Si es URL larga del API interno, guardar solo el path (/api/v1/pagos/comprobante-imagen/{uuid32}).
    """
    s = (drive_link or "").strip()
    if not s:
        return None
    m = _COMPROBANTE_IMAGEN_PATH_RE.search(s)
    if m:
        return m.group(1)
    return s[:255]


def _get_blocking_running_sync(db: Session) -> Optional[PagosGmailSync]:
    """Sync running reciente (2 h) que bloquea otra corrida."""
    return get_blocking_running_gmail_sync(db)


def _is_pipeline_running(db: Session) -> bool:
    """True si hay una sync en estado running (misma ventana que _get_blocking_running_sync)."""
    return _get_blocking_running_sync(db) is not None


def _run_pipeline_background(
    sync_id: int,
    scan_filter: str = "all",
    from_email: Optional[str] = None,
    only_message_ids: Optional[list[str]] = None,
    max_messages: Optional[int] = None,
    criterio_remitente: str = "remitente",
) -> None:
    """Ejecuta el pipeline en background con su propia sesión de BD (evita el timeout de 30s de Render/Axios)."""
    db = SessionLocal()
    logger.info(
        "[PAGOS_GMAIL] [ETAPA] Inicio pipeline background sync_id=%s scan_filter=%s from_email=%s criterio=%s only_ids=%d max_messages=%s",
        sync_id,
        scan_filter,
        from_email or "(sin remitente)",
        criterio_remitente,
        len(only_message_ids) if only_message_ids else 0,
        max_messages if max_messages is not None else "(sin tope)",
    )
    try:
        _, final_status = run_pipeline(
            db,
            existing_sync_id=sync_id,
            scan_filter=scan_filter,
            from_email=from_email,
            only_message_ids=only_message_ids,
            max_messages=max_messages,
            criterio_remitente=criterio_remitente,
        )
        if final_status == "success":
            mig = _migrar_pendientes_gmail_a_con_errores_core(db)
            if int(mig.get("migrados", 0) or 0) > 0:
                logger.info(
                    "[PAGOS_GMAIL] [ETAPA] Migración post-run Gmail -> pendientes revisión: migrados=%s omitidos=%s",
                    mig.get("migrados"),
                    mig.get("omitidos"),
                )
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


# Validación email para modo manual_redigitaliza_por_remitente (mismo criterio que gmail_service).
_FROM_EMAIL_RE = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")


def _validate_from_email(from_email: Optional[str]) -> Optional[str]:
    """Devuelve el email normalizado (lower, sin espacios) si es plausible; None si no."""
    if not from_email:
        return None
    s = str(from_email).strip().lower()
    if not s or "@" not in s:
        return None
    if not _FROM_EMAIL_RE.fullmatch(s):
        return None
    return s


@router.get("/count-pending")
def count_pending(
    scan_filter: str = "all",
    from_email: Optional[str] = Query(
        None,
        description="Solo modo manual_redigitaliza_por_remitente: acota la cuenta a correos con from:<email>.",
    ),
    db: Session = Depends(get_db),
):
    """
    Cuenta cuantos correos se procesarian sin iniciar el pipeline.
    El frontend puede mostrar "Se procesaran N correos. Iniciar? Si / No" y solo llamar
    POST /run-now si el usuario confirma (Si = inicia, No = no hace nada).
    Escaneo normal: siempre **all** (inbox + imagen/PDF, leídos y no leídos).
    Filtros especiales permitidos: error_email_rescan / manual_error_email_redigitaliza /
    manual_redigitaliza_por_remitente.
    """
    creds = get_pagos_gmail_credentials()
    if not creds:
        return {"count": 0, "scan_filter": scan_filter, "error": "no_credentials"}
    from app.services.pagos_gmail.gmail_service import build_gmail_service, count_messages_by_filter
    if scan_filter not in (
        "error_email_rescan",
        "manual_error_email_redigitaliza",
        "manual_redigitaliza_por_remitente",
    ):
        scan_filter = "all"
    from_email_norm = _validate_from_email(from_email)
    if scan_filter == "manual_redigitaliza_por_remitente" and not from_email_norm:
        return {
            "count": 0,
            "scan_filter": scan_filter,
            "error": "from_email_invalido_o_faltante",
        }
    try:
        gmail_svc = build_gmail_service(creds)
        count = count_messages_by_filter(gmail_svc, scan_filter, from_email=from_email_norm)
        return {
            "count": count,
            "scan_filter": scan_filter,
            "from_email": from_email_norm,
        }
    except Exception as e:
        logger.warning("[PAGOS_GMAIL] count-pending error: %s", e)
        return {"count": 0, "scan_filter": scan_filter, "error": str(e)[:200]}


@router.post("/run-now")
def run_now(
    background_tasks: BackgroundTasks,
    force: bool = True,
    scan_filter: str = "all",
    from_email: Optional[str] = Query(
        None,
        description="Solo modo manual_redigitaliza_por_remitente: re-escanea correos con from:<email> "
        "saltando la omisión por etiqueta de usuario únicamente para ese remitente.",
    ),
    max_messages: Optional[int] = Query(
        None,
        ge=1,
        le=10000,
        description=(
            "Tope de mensajes a procesar en esta corrida (head, mas reciente primero). "
            "Solo aplica cuando el listado proviene de messages.list (no aplica si se usa "
            "/procesar-mensajes con IDs explícitos). Si se omite, procesa todo lo que liste Gmail. "
            "Maximo absoluto: 10000."
        ),
    ),
    criterio: Optional[str] = Query(
        None,
        description=(
            "Solo modo manual_redigitaliza_por_remitente. Cómo aplicar `from_email` al filtro Gmail: "
            "'remitente' (default, `from:<correo>`); 'destinatario' (`to:<correo>`); "
            "'participante' (`from:<correo> OR to:<correo>`). Útil cuando el header `From:` real "
            "no coincide con el displayName Gmail."
        ),
        pattern="^(remitente|destinatario|participante)$",
    ),
    db: Session = Depends(get_db),
):
    """
    Inicia el pipeline en segundo plano (Gmail -> Gemini -> BD; comprobante en BD) y devuelve inmediatamente.
    Solo correos con adjuntos; candidatos imagen/PDF: incrustados, adjuntos y reenvios rfc822.
    Escaneo normal: siempre **all** (inbox + imagen/PDF, leídos y no leídos).
    Si el mensaje ya tiene cualquier etiqueta de usuario Gmail, se omite (skip total).
    Filtros especiales permitidos: **error_email_rescan**, **manual_error_email_redigitaliza** y
    **manual_redigitaliza_por_remitente** (módulo Actualizaciones > Gmail: ignora etiquetas previas
    SOLO para mensajes cuyo remitente coincide con `from_email`).
    Listado completo por paginacion Gmail; procesamiento en orden bandeja (mas reciente primero, mas antiguo al final).
    Los mensajes no leidos quedan leidos al procesarlos en la corrida.
    El frontend debe hacer polling a GET /status hasta que last_status sea 'success' o 'error'.
    El parametro force se mantiene por compatibilidad y no aplica ninguna restriccion.
    """
    _ = force
    reconcile_blocking_running_gmail_sync_if_stale(db)
    blocking = _get_blocking_running_sync(db)
    if blocking is not None:
        started = blocking.started_at.isoformat() if blocking.started_at else "?"
        if force and gmail_sync_looks_stale(blocking):
            reconcile_stale_running_gmail_sync(db, blocking)
            blocking = _get_blocking_running_sync(db)
        if blocking is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Ya hay una sincronización en curso (sync_id={blocking.id}, iniciada={started}). "
                    "Espere a que termine (consulte estado arriba). Si lleva más de 20 min sin procesar "
                    "correos, vuelva a pulsar «Procesar manualmente» (force) o espere a que el servidor "
                    "libere el bloqueo."
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
    # Escaneo normal siempre en "all"; conservar filtros especiales explícitos.
    if scan_filter not in (
        "error_email_rescan",
        "manual_error_email_redigitaliza",
        "manual_redigitaliza_por_remitente",
    ):
        scan_filter = "all"
    from_email_norm = _validate_from_email(from_email)
    if scan_filter == "manual_redigitaliza_por_remitente" and not from_email_norm:
        raise HTTPException(
            status_code=400,
            detail=(
                "scan_filter='manual_redigitaliza_por_remitente' requiere un from_email válido "
                "(ej. cliente@dominio.com)."
            ),
        )
    # El módulo "Actualizaciones > Gmail" está dedicado al lote IT Master:
    # cualquier llamada manual_redigitaliza_por_remitente con otro from_email se rechaza
    # para impedir que el flujo procese correos fuera del remitente autorizado.
    if (
        scan_filter == "manual_redigitaliza_por_remitente"
        and from_email_norm
        and from_email_norm.lower() != PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"El módulo Actualizaciones > Gmail solo procesa correos de "
                f"'{PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER}'. Remitente recibido: "
                f"'{from_email_norm}'."
            ),
        )
    criterio_norm = (criterio or "remitente").strip().lower()
    if criterio_norm not in ("remitente", "destinatario", "participante"):
        criterio_norm = "remitente"
    if (
        scan_filter == "manual_redigitaliza_por_remitente"
        and from_email_norm
        and from_email_norm.lower() == PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER
    ):
        # IT Master es la cuenta Gmail conectada/buzón receptor; este módulo debe leer
        # INBOX como destinatario, no `from:`. gmail_service también lo fuerza por defensa.
        criterio_norm = "destinatario"
    # Crear registro de sync de inmediato (evita que un segundo click arranque otro pipeline)
    sync = PagosGmailSync(status="running", emails_processed=0, files_processed=0)
    db.add(sync)
    db.commit()
    db.refresh(sync)
    sync_id = sync.id
    # Lanzar pipeline en segundo plano; el cliente hace polling a /status
    background_tasks.add_task(
        _run_pipeline_background,
        sync_id,
        scan_filter,
        from_email_norm,
        None,
        max_messages,
        criterio_norm,
    )
    return {
        "sync_id": sync_id,
        "status": "running",
        "emails_processed": 0,
        "files_processed": 0,
        "scan_filter": scan_filter,
        "from_email": from_email_norm,
        "max_messages": max_messages,
        "criterio": criterio_norm,
    }


@router.get("/status")
def status(db: Session = Depends(get_db)):
    """Ultima ejecucion (manual o programada); next_run_approx solo si el escaneo Gmail programado esta registrado en el scheduler."""
    reconcile_blocking_running_gmail_sync_if_stale(db)
    last = db.execute(select(PagosGmailSync).order_by(desc(PagosGmailSync.started_at)).limit(1)).scalars().first()
    if last is not None and reconcile_stale_running_gmail_sync(db, last):
        db.refresh(last)
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
        "running_looks_stale": bool(last and gmail_sync_looks_stale(last)),
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


def _parse_fecha_pago_gmail_temporal(raw_fecha: Optional[str], fallback_dt: datetime) -> datetime:
    """Convierte fecha textual de gmail_temporal a datetime (00:00:00)."""
    txt = (raw_fecha or "").strip()
    if txt:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                d = datetime.strptime(txt, fmt)
                return d.replace(hour=0, minute=0, second=0, microsecond=0)
            except ValueError:
                continue
    return fallback_dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _migrar_pendientes_gmail_a_con_errores_core(db: Session) -> dict:
    """
    Núcleo de migración de pendientes Gmail: mueve filas de gmail_temporal a pagos_con_errores.
    Se reutiliza tanto en endpoint manual como post-proceso automático.
    """
    filas = db.execute(
        select(GmailTemporal).order_by(GmailTemporal.id.asc())
    ).scalars().all()
    if not filas:
        return {
            "migrados": 0,
            "omitidos": 0,
            "eliminados_temporal": 0,
            "mensaje": "Sin pendientes en gmail_temporal.",
        }

    migrados = 0
    omitidos = 0
    eliminados_temporal = 0

    for row in filas:
        try:
            with db.begin_nested():
                fallback_created = row.created_at or datetime.utcnow()
                fecha_pago = _parse_fecha_pago_gmail_temporal(
                    row.fecha_pago, fallback_created
                )
                cedula = formatear_cedula(row.cedula or "")
                monto_txt = format_monto_excel_pagos_gmail(row.monto or "")
                try:
                    monto_num = float(monto_txt) if monto_txt else 0.0
                except ValueError:
                    monto_num = 0.0

                numero_base = normalize_documento(row.numero_referencia)
                numero_doc = compose_numero_documento_almacenado(
                    numero_base or f"GMAILTMP-{row.id}", None
                )

                if numero_doc and numero_documento_ya_registrado(db, numero_doc):
                    db.execute(
                        delete(GmailTemporal).where(GmailTemporal.id == row.id)
                    )
                    eliminados_temporal += 1
                    omitidos += 1
                    continue

                observaciones = "Pendiente desde Gmail (no autoconciliado)"
                if monto_num <= 0:
                    observaciones = (
                        f"{observaciones}; monto no interpretable: {(row.monto or '').strip() or 'vacío'}"
                    )[:255]

                doc_ruta = _documento_ruta_desde_gmail_temporal(
                    getattr(row, "drive_link", None)
                )

                nuevo = PagoConError(
                    prestamo_id=None,
                    cedula_cliente=cedula or None,
                    fecha_pago=fecha_pago,
                    monto_pagado=monto_num,
                    numero_documento=numero_doc,
                    institucion_bancaria=(row.banco or None),
                    estado="PENDIENTE",
                    conciliado=False,
                    usuario_registro="GMAIL_PIPELINE",
                    notas=(
                        f"Asunto: {(row.asunto or '').strip()} | "
                        f"Correo: {(row.correo_origen or '').strip()}"
                    )[:1000],
                    referencia_pago=(numero_base or f"GMAILTMP-{row.id}")[:100],
                    observaciones=observaciones,
                    documento_ruta=doc_ruta,
                    documento_nombre=("Comprobante Gmail" if doc_ruta else None),
                )
                db.add(nuevo)
                db.flush()
                db.execute(delete(GmailTemporal).where(GmailTemporal.id == row.id))
                eliminados_temporal += 1
                migrados += 1
        except Exception:
            omitidos += 1
            continue

    db.commit()
    return {
        "migrados": migrados,
        "omitidos": omitidos,
        "eliminados_temporal": eliminados_temporal,
        "mensaje": (
            f"Migración completada: {migrados} a pagos_con_errores, "
            f"{omitidos} omitidos, {eliminados_temporal} removidos de gmail_temporal."
        ),
    }


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


@router.post("/migrar-pendientes-a-con-errores", response_model=dict)
def migrar_pendientes_a_con_errores(db: Session = Depends(get_db)):
    """
    Mueve pendientes no autoconciliados de `gmail_temporal` a `pagos_con_errores`.
    Garantiza que, tras "Procesar manualmente", todo quede en A (pagos) o B (pendientes de revisión).
    """
    try:
        return _migrar_pendientes_gmail_a_con_errores_core(db)
    except Exception as e:
        db.rollback()
        logger.exception("Error migrando gmail_temporal -> pagos_con_errores: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


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
    Ítems de sync cuyo comprobante A–D/NR pasó validadores y además aplicó a cuotas (traza CUOTAS_OK):
    no deben repetirse en Excel de revisión.
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
                PagosGmailAbcdCuotasTraza.etapa_final == "CUOTAS_OK",
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


_GMAIL_EXCEL_EXPORT_DEPRECATED = (
    "La exportación Excel del pipeline Gmail está descontinuada. "
    "Tras procesar correos: autoconciliados en Pagos; pendientes en Pagos con errores "
    "(migración automática al terminar run-now)."
)


@router.get("/download-excel")
def download_excel(
    fecha: Optional[str] = None,
    solo_duplicados_documento: Annotated[
        bool,
        Query(
            description="Solo filas banco plantilla A–D cuyo serial ya existe en pagos o pagos_con_errores (revisión manual).",
        ),
    ] = False,
    excluir_duplicados_documento: Annotated[
        bool,
        Query(
            description="Excluye esas filas duplicadas; el resto (incl. NR y no-ABCD) sigue en el Excel.",
        ),
    ] = False,
    db: Session = Depends(get_db),
):
    """Descontinuado: revisar en Pagos / Pagos con errores."""
    del fecha, solo_duplicados_documento, excluir_duplicados_documento, db
    raise HTTPException(status_code=410, detail=_GMAIL_EXCEL_EXPORT_DEPRECATED)



@router.get("/download-excel-temporal")
def download_excel_temporal(
    solo_duplicados_documento: Annotated[
        bool,
        Query(
            description="Solo filas banco plantilla A–D cuyo serial ya existe en pagos o pagos_con_errores (revisión manual).",
        ),
    ] = False,
    excluir_duplicados_documento: Annotated[
        bool,
        Query(
            description="Excluye esas filas duplicadas; el resto sigue en el Excel.",
        ),
    ] = False,
    db: Session = Depends(get_db),
):
    """Descontinuado: pendientes en Pagos con errores tras run-now."""
    del solo_duplicados_documento, excluir_duplicados_documento, db
    raise HTTPException(status_code=410, detail=_GMAIL_EXCEL_EXPORT_DEPRECATED)

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
            "nota": "Cuerpo incrustado + adjuntos imagen/PDF + message/rfc822 (.eml); cada candidato se evalúa según prompts/reglas",
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


def _ids_temporal_autoconciliados_residuales(
    db: Session, *, limit: int = 5000
) -> list[int]:
    """
    Detecta filas residuales en gmail_temporal que ya tienen alta automática OK
    con aplicación real a cuotas (CUOTAS_OK con pago_id) por trazabilidad de sync_item.
    """
    q = (
        select(GmailTemporal.id)
        .join(
            PagosGmailSyncItem,
            and_(
                PagosGmailSyncItem.gmail_message_id == GmailTemporal.gmail_message_id,
                PagosGmailSyncItem.gmail_thread_id == GmailTemporal.gmail_thread_id,
                PagosGmailSyncItem.numero_referencia == GmailTemporal.numero_referencia,
                PagosGmailSyncItem.cedula == GmailTemporal.cedula,
            ),
        )
        .join(
            PagosGmailAbcdCuotasTraza,
            PagosGmailAbcdCuotasTraza.sync_item_id == PagosGmailSyncItem.id,
        )
        .where(
            GmailTemporal.gmail_message_id.isnot(None),
            GmailTemporal.gmail_thread_id.isnot(None),
            GmailTemporal.numero_referencia.isnot(None),
            GmailTemporal.cedula.isnot(None),
            PagosGmailAbcdCuotasTraza.etapa_final == "CUOTAS_OK",
            PagosGmailAbcdCuotasTraza.pago_id.isnot(None),
        )
        .limit(limit)
    )
    rows = db.execute(q).scalars().all()
    return list(dict.fromkeys(int(x) for x in rows if x is not None))


@router.get("/verificacion-proceso-conexiones")
def verificacion_proceso_conexiones(db: Session = Depends(get_db)):
    """
    Auditoría operativa: estado de conexiones y consistencia post-escaneo.
    """
    from app.services.pagos_gmail.credentials import get_pagos_gmail_credentials
    from app.services.pagos_gmail.gmail_service import build_gmail_service, count_messages_by_filter

    creds_ok = False
    gmail_ok = False
    gmail_count_all = None
    cred_error = None
    gmail_error = None

    try:
        creds = get_pagos_gmail_credentials()
        creds_ok = bool(creds)
        if creds_ok:
            try:
                gmail_svc = build_gmail_service(creds)
                gmail_count_all = int(count_messages_by_filter(gmail_svc, "all"))
                gmail_ok = True
            except Exception as e:
                gmail_error = str(e)[:500]
    except Exception as e:
        cred_error = str(e)[:500]

    sync_items_count = int(
        db.scalar(select(func.count()).select_from(PagosGmailSyncItem)) or 0
    )
    temporal_count = int(
        db.scalar(select(func.count()).select_from(GmailTemporal)) or 0
    )
    traza_ok_count = int(
        db.scalar(
            select(func.count())
            .select_from(PagosGmailAbcdCuotasTraza)
            .where(
                PagosGmailAbcdCuotasTraza.etapa_final == "CUOTAS_OK",
                PagosGmailAbcdCuotasTraza.pago_id.isnot(None),
            )
        )
        or 0
    )
    residual_ids = _ids_temporal_autoconciliados_residuales(db)

    return {
        "conexiones": {
            "credenciales_ok": creds_ok,
            "gmail_ok": gmail_ok,
            "gmail_count_all": gmail_count_all,
            "credenciales_error": cred_error,
            "gmail_error": gmail_error,
        },
        "proceso": {
            "sync_items_total": sync_items_count,
            "gmail_temporal_total": temporal_count,
            "traza_autoconciliados_ok_total": traza_ok_count,
            "gmail_temporal_residuales_autoconciliados": len(residual_ids),
            "muestra_ids_residuales": residual_ids[:20],
        },
    }


@router.post("/limpiar-temporal-autoconciliados")
def limpiar_temporal_autoconciliados(db: Session = Depends(get_db)):
    """
    Limpia filas residuales de gmail_temporal que ya están autoconciliadas en pagos.
    """
    ids = _ids_temporal_autoconciliados_residuales(db, limit=20000)
    if not ids:
        return {"eliminados": 0, "mensaje": "Sin residuales autoconciliados en gmail_temporal."}

    try:
        db.execute(delete(GmailTemporal).where(GmailTemporal.id.in_(ids)))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo limpiar gmail_temporal residual: {str(e)[:400]}",
        ) from e

    return {
        "eliminados": len(ids),
        "mensaje": "Limpieza de residuales autoconciliados completada.",
        "ids_muestra": ids[:20],
    }


# ---------------------------------------------------------------------------
# Listado/acciones por sync_item (módulo Actualizaciones > Gmail)
# ---------------------------------------------------------------------------


def _sync_item_fecha_correo(item: PagosGmailSyncItem) -> Optional[str]:
    """
    Fecha del correo (YYYY-MM-DD) reconstruida desde sheet_name si está disponible.
    sheet_name 'Pagos_Cobros_9Marzo2026' -> '2026-03-09'.
    Si no se puede parsear, fallback al created_at del item (UTC) en YYYY-MM-DD.
    """
    from app.services.pagos_gmail.helpers import parse_date_from_sheet_name
    d = parse_date_from_sheet_name(item.sheet_name or "") if item.sheet_name else None
    if d is not None:
        return d.strftime("%Y-%m-%d")
    if item.created_at:
        return item.created_at.strftime("%Y-%m-%d")
    return None


def _sync_item_comprobante_url(item: PagosGmailSyncItem) -> Optional[str]:
    """
    URL servible del comprobante: normaliza drive_link a path interno cuando aplica.
    Si es URL externa (Drive heredado), se devuelve tal cual.
    """
    raw = (item.drive_link or "").strip()
    if not raw:
        return None
    m = _COMPROBANTE_IMAGEN_PATH_RE.search(raw)
    if m:
        return m.group(1)
    return raw[:1000]


def _cedula_placeholder_error(valor: Optional[str]) -> bool:
    s = (valor or "").strip().upper()
    return not s or s in {"ERROR", "ERROR EMAIL", "ERROR_EMAIL"}


def _cedula_sync_item_efectiva(db: Session, item: PagosGmailSyncItem) -> str:
    """
    Lote IT Master: la cédula del cliente viene del asunto del correo maestro.

    Si una fila vieja quedó con `ERROR` por una extracción anterior, se repara aquí
    antes de mostrar, guardar o migrar a revisión manual.
    """
    cedula_actual = formatear_cedula(item.cedula or "")
    if (
        (item.correo_origen or "").strip().lower() == PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER
        and _cedula_placeholder_error(cedula_actual)
    ):
        cedula_asunto = extract_lote_it_master_cedula_from_subject(item.asunto)
        cedula_resuelta = resolver_cedula_almacenada_en_clientes(db, cedula_asunto)
        if cedula_resuelta:
            item.cedula = cedula_resuelta
            db.flush()
            return cedula_resuelta
    return cedula_actual


def _sync_item_duplicado_en_pagos(
    db: Session,
    numero_referencia: Optional[str],
    cedula_item: Optional[str] = None,
) -> tuple[bool, Optional[int], Optional[int]]:
    """
    Devuelve (duplicado_bool, pago_id_si_existe, prestamo_id_si_existe).

    Reutiliza primer_pago_cartera_por_documento (busca en `pagos.numero_documento` con normalización).
    Cuando se proporciona `cedula_item`, el resultado se considera duplicado SOLO si el pago
    encontrado pertenece al **mismo cliente** (misma cédula normalizada). Esto evita marcar como
    duplicados los seriales que el banco pudo reusar entre clientes diferentes.

    Si `cedula_item` no se proporciona (compatibilidad con llamadas antiguas), comportamiento
    legacy: cualquier coincidencia por documento marca duplicado.
    """
    from app.services.pago_numero_documento import primer_pago_cartera_por_documento
    from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd
    from app.models.pago import Pago

    ref = (numero_referencia or "").strip()
    if not ref:
        return False, None, None
    pid, prid = primer_pago_cartera_por_documento(db, ref)
    if pid is None:
        return False, None, None

    cedula_norm_item = texto_cedula_comparable_bd(cedula_item) if cedula_item else ""
    if not cedula_norm_item:
        return True, pid, prid

    pago_row = db.execute(
        select(Pago.cedula_cliente).where(Pago.id == pid)
    ).first()
    if pago_row is None:
        return False, None, None
    cedula_pago_norm = texto_cedula_comparable_bd(pago_row[0] or "")
    if cedula_pago_norm and cedula_pago_norm == cedula_norm_item:
        return True, pid, prid
    return False, None, None


@router.get("/sync-items")
def listar_sync_items(
    correo: Optional[str] = Query(
        None,
        description="OBLIGATORIO en el módulo Actualizaciones > Gmail: correo_origen exacto "
        "(case-insensitive). Sin él, este endpoint NO lista nada (no se expone el histórico "
        "global de la cola Gmail).",
    ),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    excluir_autoconciliados: bool = Query(
        True,
        description="Excluye filas con traza CUOTAS_OK + pago_id (ya en cartera, no aporta revisión).",
    ),
    db: Session = Depends(get_db),
):
    """
    Lista filas de `pagos_gmail_sync_item` del remitente indicado.
    No se expone el histórico global: si no se envía `correo`, el endpoint devuelve vacío.
    Devuelve los campos exactos que necesita la UI: fecha del correo, imagen (URL), banco,
    fecha de pago, monto, serial, asunto y un indicador `duplicado_en_pagos` con el
    `pago_id_existente` cuando aplica.
    """
    correo_lc = (correo or "").strip().lower() or None
    if not correo_lc:
        return {
            "total": 0,
            "items": [],
            "limit": limit,
            "offset": offset,
            "mensaje": "Indica un remitente (parámetro 'correo') para listar sus comprobantes.",
        }

    # Match exacto (no LIKE %x%) para no mezclar dominios o cuentas similares.
    q = (
        select(PagosGmailSyncItem)
        .where(func.lower(PagosGmailSyncItem.correo_origen) == correo_lc)
        .order_by(desc(PagosGmailSyncItem.created_at))
    )
    # Excluir filas con alta automática OK aplicada a cuotas (CUOTAS_OK + pago_id).
    if excluir_autoconciliados:
        sub_ok = (
            select(PagosGmailAbcdCuotasTraza.sync_item_id)
            .where(
                PagosGmailAbcdCuotasTraza.etapa_final == "CUOTAS_OK",
                PagosGmailAbcdCuotasTraza.pago_id.isnot(None),
                PagosGmailAbcdCuotasTraza.sync_item_id.isnot(None),
            )
        )
        q = q.where(PagosGmailSyncItem.id.notin_(sub_ok))

    count_q = (
        select(func.count())
        .select_from(PagosGmailSyncItem)
        .where(func.lower(PagosGmailSyncItem.correo_origen) == correo_lc)
    )
    total = int(db.scalar(count_q) or 0)

    rows = db.execute(q.offset(offset).limit(limit)).scalars().all()
    items: list[dict] = []
    for r in rows:
        cedula_item = _cedula_sync_item_efectiva(db, r)
        duplicado, pago_id_exist, prestamo_id_exist = _sync_item_duplicado_en_pagos(
            db, r.numero_referencia, cedula_item
        )
        revision_monto_alto = monto_gmail_sync_requiere_revision_manual_usd(r.monto)
        items.append(
            {
                "id": r.id,
                "sync_id": r.sync_id,
                "fecha_correo": _sync_item_fecha_correo(r),
                "comprobante_url": _sync_item_comprobante_url(r),
                "banco": r.banco,
                "fecha_pago": r.fecha_pago,
                "cedula": cedula_item,
                "monto": r.monto,
                "numero_referencia": r.numero_referencia,
                "correo_origen": r.correo_origen,
                "asunto": r.asunto,
                "gmail_message_id": r.gmail_message_id,
                "gmail_thread_id": r.gmail_thread_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "duplicado_en_pagos": duplicado,
                "pago_id_existente": pago_id_exist,
                "prestamo_id_existente": prestamo_id_exist,
                "requiere_revision_manual_monto": revision_monto_alto,
            }
        )
    return {"total": total, "items": items, "limit": limit, "offset": offset}


def _pago_con_error_desde_sync_item(
    db: Session, item: PagosGmailSyncItem
) -> tuple[PagoConError, bool]:
    """
    Construye y persiste un PagoConError a partir de un sync_item.
    Mismas reglas que _migrar_pendientes_gmail_a_con_errores_core, acotadas a una fila:
    - normaliza referencia y compone numero_documento.
    - parsea fecha_pago a datetime (00:00:00).
    - cédula formateada (PagoConError acepta sin FK a clientes).
    - drive_link -> documento_ruta (path interno si aplica).
    Devuelve (fila_pago_con_error, reutilizada_bool). Si ya existe una fila pendiente
    con el mismo `numero_documento` (índice único ux_pagos_con_errores_numero_documento_btrim),
    la reutiliza/actualiza en lugar de insertar otra. Esto hace idempotente el botón
    "Editar" cuando el operador pulsa varias veces o cuando otro sync_item con el mismo
    serial ya fue migrado a revisión manual.
    """
    fallback_dt = item.created_at or datetime.utcnow()
    fecha_pago = _parse_fecha_pago_gmail_temporal(item.fecha_pago, fallback_dt)
    cedula = _cedula_sync_item_efectiva(db, item)
    monto_txt = format_monto_excel_pagos_gmail(item.monto or "")
    try:
        monto_num = float(monto_txt) if monto_txt else 0.0
    except ValueError:
        monto_num = 0.0

    numero_base = normalize_documento(item.numero_referencia)
    numero_doc = compose_numero_documento_almacenado(
        numero_base or f"GMAILSI-{item.id}", None
    )
    numero_doc_key = (numero_doc or "").strip().upper()

    observaciones = "Pendiente desde Gmail (guardado manual desde módulo Actualizaciones > Gmail)"
    if monto_gmail_sync_requiere_revision_manual_usd(item.monto):
        observaciones = (
            f"{observaciones}; monto > {PAGOS_GMAIL_UMBRAL_REVISION_MANUAL_USD} "
            "(revision manual obligatoria)"
        )[:255]
    if monto_num <= 0:
        observaciones = (
            f"{observaciones}; monto no interpretable: {(item.monto or '').strip() or 'vacío'}"
        )[:255]

    doc_ruta = _documento_ruta_desde_gmail_temporal(getattr(item, "drive_link", None))
    cedula_resuelta = resolver_cedula_almacenada_en_clientes(db, cedula)
    prestamo_id_auto: Optional[int] = None
    if cedula_resuelta:
        cliente = db.execute(
            select(Cliente).where(Cliente.cedula == cedula_resuelta)
        ).scalars().first()
        if cliente is not None:
            prestamos = (
                db.execute(
                    select(Prestamo)
                    .where(
                        Prestamo.cliente_id == cliente.id,
                        Prestamo.estado == "APROBADO",
                    )
                    .order_by(Prestamo.id)
                )
                .scalars()
                .all()
            )
            if len(prestamos) == 1:
                prestamo_id_auto = int(prestamos[0].id)
            elif len(prestamos) > 1:
                observaciones = (
                    f"{observaciones}; cédula con {len(prestamos)} préstamos APROBADOS, "
                    "requiere seleccionar préstamo en revisión manual"
                )[:255]
            else:
                observaciones = (
                    f"{observaciones}; sin préstamo APROBADO para autoconciliar"
                )[:255]
    else:
        observaciones = (
            f"{observaciones}; cédula no encontrada en clientes para autoconciliar"
        )[:255]

    def _buscar_existente_por_numero() -> Optional[PagoConError]:
        if not numero_doc_key:
            return None
        return db.execute(
            select(PagoConError).where(
                func.upper(func.trim(PagoConError.numero_documento)) == numero_doc_key
            )
        ).scalars().first()

    existente = _buscar_existente_por_numero()
    if existente is not None:
        existente.prestamo_id = existente.prestamo_id or prestamo_id_auto
        existente.cedula_cliente = existente.cedula_cliente or cedula_resuelta or (cedula or None)
        existente.fecha_pago = fecha_pago
        existente.monto_pagado = monto_num
        existente.institucion_bancaria = (item.banco or None)
        existente.estado = existente.estado or "PENDIENTE"
        existente.conciliado = bool(existente.conciliado) if existente.conciliado is not None else False
        existente.usuario_registro = existente.usuario_registro or "GMAIL_PIPELINE"
        if doc_ruta and not existente.documento_ruta:
            existente.documento_ruta = doc_ruta
            existente.documento_nombre = "Comprobante Gmail"
        existente.notas = (
            f"Asunto: {(item.asunto or '').strip()} | "
            f"Correo: {(item.correo_origen or '').strip()}"
        )[:1000]
        existente.referencia_pago = (numero_base or f"GMAILSI-{item.id}")[:100]
        existente.observaciones = observaciones
        db.flush()
        db.refresh(existente)
        return existente, True

    nuevo = PagoConError(
        prestamo_id=prestamo_id_auto,
        cedula_cliente=cedula_resuelta or cedula or None,
        fecha_pago=fecha_pago,
        monto_pagado=monto_num,
        numero_documento=numero_doc,
        institucion_bancaria=(item.banco or None),
        estado="PENDIENTE",
        conciliado=False,
        usuario_registro="GMAIL_PIPELINE",
        notas=(
            f"Asunto: {(item.asunto or '').strip()} | "
            f"Correo: {(item.correo_origen or '').strip()}"
        )[:1000],
        referencia_pago=(numero_base or f"GMAILSI-{item.id}")[:100],
        observaciones=observaciones,
        documento_ruta=doc_ruta,
        documento_nombre=("Comprobante Gmail" if doc_ruta else None),
    )
    try:
        # Savepoint: si otro proceso/fila ya creó el mismo numero_documento, el
        # UniqueViolation no deja abortada la transacción exterior del endpoint.
        with db.begin_nested():
            db.add(nuevo)
            db.flush()
        db.refresh(nuevo)
        return nuevo, False
    except IntegrityError as exc:
        logger.info(
            "[PAGOS_GMAIL] PagoConError ya existía al migrar sync_item=%s numero_documento=%s; reutilizando fila existente. err=%s",
            getattr(item, "id", None),
            numero_doc,
            str(exc)[:200],
        )
        existente = _buscar_existente_por_numero()
        if existente is None:
            raise
        if doc_ruta and not existente.documento_ruta:
            existente.documento_ruta = doc_ruta
            existente.documento_nombre = "Comprobante Gmail"
        existente.prestamo_id = existente.prestamo_id or prestamo_id_auto
        existente.cedula_cliente = existente.cedula_cliente or cedula_resuelta or (cedula or None)
        existente.fecha_pago = fecha_pago
        existente.monto_pagado = monto_num
        existente.institucion_bancaria = (item.banco or None)
        existente.estado = existente.estado or "PENDIENTE"
        existente.referencia_pago = (numero_base or f"GMAILSI-{item.id}")[:100]
        existente.observaciones = observaciones
        db.flush()
        db.refresh(existente)
        return existente, True


def _eliminar_filas_gmail_relacionadas(db: Session, item: PagosGmailSyncItem) -> int:
    """
    Borra del lado Gmail (sync_item + filas equivalentes en gmail_temporal) cuando ya pasamos
    a pagos_con_errores. Evita que la misma fila vuelva a verse en la tabla.
    Devuelve filas afectadas en gmail_temporal.
    """
    where_temp = [
        GmailTemporal.numero_referencia == item.numero_referencia,
        GmailTemporal.correo_origen == item.correo_origen,
    ]
    if item.gmail_message_id:
        where_temp.append(GmailTemporal.gmail_message_id == item.gmail_message_id)
    res = db.execute(delete(GmailTemporal).where(and_(*where_temp)))
    db.delete(item)
    return int(getattr(res, "rowcount", 0) or 0)


@router.post("/sync-items/limpiar-remitente")
def limpiar_sync_items_remitente(
    correo: str = Query(..., description="Correo origen del módulo Gmail a limpiar."),
    db: Session = Depends(get_db),
):
    """
    Limpieza explícita del módulo Actualizaciones > Gmail.

    Borra únicamente la cola local del remitente fijo IT Master (`pagos_gmail_sync_item`
    y `gmail_temporal`). No toca `pagos`, `pagos_con_errores` ni Gmail.
    Deja la UI en cero para que la próxima corrida sea un escaneo fresco.
    """
    correo_lc = _validate_from_email(correo)
    if not correo_lc:
        raise HTTPException(status_code=400, detail="Correo inválido.")
    if correo_lc.lower() != PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Este módulo solo permite limpiar '{PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER}'."
            ),
        )
    try:
        res_si = db.execute(
            delete(PagosGmailSyncItem).where(
                func.lower(PagosGmailSyncItem.correo_origen) == correo_lc
            )
        )
        res_gt = db.execute(
            delete(GmailTemporal).where(
                func.lower(GmailTemporal.correo_origen) == correo_lc
            )
        )
        db.commit()
        borrados_si = int(getattr(res_si, "rowcount", 0) or 0)
        borrados_gt = int(getattr(res_gt, "rowcount", 0) or 0)
        logger.info(
            "[PAGOS_GMAIL] limpiar-remitente correo=%s sync_items=%d gmail_temporal=%d",
            correo_lc,
            borrados_si,
            borrados_gt,
        )
        return {
            "ok": True,
            "correo": correo_lc,
            "sync_items_eliminados": borrados_si,
            "gmail_temporal_eliminados": borrados_gt,
            "mensaje": (
                f"Limpieza completada: {borrados_si} fila(s) de resultados y "
                f"{borrados_gt} temporal(es) eliminados."
            ),
        }
    except Exception as e:
        db.rollback()
        logger.exception("[PAGOS_GMAIL] limpiar-remitente fallo correo=%s: %s", correo_lc, e)
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo limpiar resultados Gmail: {str(e)[:400]}",
        ) from e


@router.post("/sync-items/{item_id}/guardar")
def guardar_sync_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    """
    Acción "Guardar" desde la tabla del módulo Actualizaciones > Gmail.

    Encadena en una sola llamada:
    1) Migra la fila `pagos_gmail_sync_item` a `pagos_con_errores` (mismas reglas que
       `_migrar_pendientes_gmail_a_con_errores_core` para una sola fila).
    2) Llama internamente al endpoint `pagos_con_errores/mover-a-pagos`, que:
       - valida duplicado en `pagos`,
       - resuelve la cédula contra `clientes` (FK fk_pagos_cedula),
       - crea el `Pago` con conciliado/verificado SI cuando hay préstamo + monto > 0,
       - aplica el pago a cuotas con la cascada vigente
         (`_aplicar_pago_a_cuotas_interno`; ver regla `pagos-cascada-no-fifo`).

    No invade reglas de revisión manual: las validaciones se hacen exactamente como en el
    flujo `pagos_con_errores`. Si falla la migración (p. ej. duplicado de documento o cliente
    inexistente), se devuelve el detalle y la fila permanece en revisión manual.
    """
    from app.api.v1.endpoints.pagos_con_errores.routes import (
        mover_a_pagos_normales,
        EliminarPorDescargaBody,
    )

    item = db.get(PagosGmailSyncItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"sync_item {item_id} no encontrado")

    if monto_gmail_sync_requiere_revision_manual_usd(item.monto):
        return {
            "ok": False,
            "movido_a_pagos": False,
            "cuotas_aplicadas": 0,
            "pago_con_error_pendiente": False,
            "errores": [
                f"Pagos mayores a {PAGOS_GMAIL_UMBRAL_REVISION_MANUAL_USD} requieren "
                "revision manual. Use Editar para validar y aplicar con cascada."
            ],
            "mensaje": (
                f"Monto > {PAGOS_GMAIL_UMBRAL_REVISION_MANUAL_USD}: no se puede "
                "autoconciliar con Guardar. Use Editar."
            ),
        }

    try:
        with db.begin_nested():
            cedula_item = _cedula_sync_item_efectiva(db, item)
            # Si la referencia ya está aplicada en cartera, no crear nada nuevo: avisar.
            duplicado, pago_id_exist, _prid = _sync_item_duplicado_en_pagos(
                db, item.numero_referencia, cedula_item
            )
            if duplicado:
                return {
                    "ok": False,
                    "movido_a_pagos": False,
                    "cuotas_aplicadas": 0,
                    "ya_en_pagos": True,
                    "pago_id_existente": pago_id_exist,
                    "pago_con_error_pendiente": False,
                    "errores": [
                        "No se puede guardar automáticamente: el serial ya existe en pagos. "
                        "Use Editar para agregar sufijo o Eliminar si ya fue aplicado."
                    ],
                    "mensaje": (
                        f"Ya existe pago con número {item.numero_referencia or '(s/r)'} "
                        f"en cartera (pago_id={pago_id_exist}). No se creó otro pago."
                    ),
                }

            nuevo_pe, _pe_reutilizado = _pago_con_error_desde_sync_item(db, item)
            pago_con_error_id = int(nuevo_pe.id)

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception(
            "[PAGOS_GMAIL] guardar_sync_item: fallo creando pago_con_error item_id=%s: %s",
            item_id,
            e,
        )
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo preparar la fila para guardar: {str(e)[:400]}",
        ) from e

    pago_preparado = db.get(PagoConError, pago_con_error_id)
    if pago_preparado is None:
        raise HTTPException(
            status_code=500,
            detail=f"Pago_con_error {pago_con_error_id} no encontrado tras preparar la fila.",
        )
    if not getattr(pago_preparado, "prestamo_id", None):
        return {
            "ok": False,
            "movido_a_pagos": False,
            "cuotas_aplicadas": 0,
            "pago_con_error_id": pago_con_error_id,
            "pago_con_error_pendiente": True,
            "errores": [
                "No se puede autoconciliar desde Gmail: no hay un préstamo APROBADO único "
                "para la cédula. Use Editar para seleccionar/corregir antes de aplicar."
            ],
            "ya_cargado_eliminados": [],
            "mensaje": "La fila quedó en revisión manual; no se creó pago ni se aplicaron cuotas.",
        }
    if float(getattr(pago_preparado, "monto_pagado", 0) or 0) <= 0:
        return {
            "ok": False,
            "movido_a_pagos": False,
            "cuotas_aplicadas": 0,
            "pago_con_error_id": pago_con_error_id,
            "pago_con_error_pendiente": True,
            "errores": [
                "No se puede autoconciliar desde Gmail: el monto no es mayor que cero. "
                "Use Editar para corregirlo."
            ],
            "ya_cargado_eliminados": [],
            "mensaje": "La fila quedó en revisión manual; no se creó pago ni se aplicaron cuotas.",
        }

    # Mover a pagos aplicando cascada de cuotas. Reutilizamos el endpoint canónico.
    try:
        resultado = mover_a_pagos_normales(
            EliminarPorDescargaBody(ids=[pago_con_error_id]),
            db=db,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "[PAGOS_GMAIL] guardar_sync_item: fallo en mover_a_pagos_normales pe_id=%s: %s",
            pago_con_error_id,
            e,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                f"Pago_con_error creado (id={pago_con_error_id}) pero falló mover-a-pagos. "
                f"Revíselo en pagos_con_errores. Detalle: {str(e)[:400]}"
            ),
        ) from e

    movidos = int(resultado.get("movidos", 0) or 0) if isinstance(resultado, dict) else 0
    errores = (
        resultado.get("errores_procesamiento", []) if isinstance(resultado, dict) else []
    )
    ya_cargado = (
        resultado.get("ya_cargado_eliminados", []) if isinstance(resultado, dict) else []
    )
    cuotas_aplicadas = (
        int(resultado.get("cuotas_aplicadas", 0) or 0) if isinstance(resultado, dict) else 0
    )
    if movidos > 0 or bool(ya_cargado):
        try:
            item_limpieza = db.get(PagosGmailSyncItem, item_id)
            if item_limpieza is not None:
                _eliminar_filas_gmail_relacionadas(db, item_limpieza)
                db.commit()
        except Exception as e:
            db.rollback()
            logger.exception(
                "[PAGOS_GMAIL] guardar_sync_item: pago procesado pero no se pudo limpiar sync_item=%s: %s",
                item_id,
                e,
            )
            raise HTTPException(
                status_code=500,
                detail=(
                    "El pago fue procesado, pero no se pudo limpiar la fila Gmail. "
                    f"Refresque y reintente eliminarla. Detalle: {str(e)[:400]}"
                ),
            ) from e

    return {
        "ok": movidos > 0 or bool(ya_cargado),
        "movido_a_pagos": movidos > 0,
        "cuotas_aplicadas": cuotas_aplicadas,
        "pago_con_error_id": pago_con_error_id,
        "pago_con_error_pendiente": bool(errores) and movidos == 0,
        "errores": errores,
        "ya_cargado_eliminados": ya_cargado,
        "mensaje": (
            "Pago movido a cartera y aplicado a cuotas (cascada)."
            if movidos > 0
            else (
                "La fila quedó en pagos_con_errores para revisión manual "
                f"(pe_id={pago_con_error_id}). Ver detalle en `errores`."
            )
        ),
    }


@router.post("/sync-items/{item_id}/migrar-a-pendientes")
def migrar_sync_item_a_pendientes(
    item_id: int,
    db: Session = Depends(get_db),
):
    """
    Acción "Editar" desde la tabla del módulo Actualizaciones > Gmail.

    Migra la fila `pagos_gmail_sync_item` a `pagos_con_errores` y devuelve el
    `PagoConError` serializado (mismo shape que GET /pagos/con-errores) para que
    el frontend abra el modal de **revisión manual** sobre ese pago_con_error
    (`RegistrarPagoForm` con `esPagoConError=true` + `modoGuardarYProcesar=true`
    + `mostrarCampoCodigoDocumento=true`).

    A diferencia de `/sync-items/{id}/guardar`, este endpoint **no** llama a
    `mover_a_pagos_normales`: deja la fila en `pagos_con_errores` para que el
    operador revise/corrija campos antes de aplicarla con cascada de cuotas. Toda
    la validación final (FK cliente, formato de serial, duplicado documento,
    monto>0) corre en el flujo estándar de revisión manual.

    Si el serial (`numero_referencia`) ya existe en cartera (`pagos`), igualmente
    se migra a `pagos_con_errores` y se devuelve `duplicado_documento_en_pagos=true`
    en `pago_con_error`. Así el operador puede abrir el modal y agregar un sufijo
    (`codigo_documento`) para diferenciar el pago - mismo flujo que en
    `EditarRevisionManual` y `PagosList`/`pagos_con_errores`.
    """
    from app.api.v1.endpoints.pagos_con_errores.routes import (
        _pago_con_error_to_response,
    )

    item = db.get(PagosGmailSyncItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"sync_item {item_id} no encontrado")

    cedula_item = _cedula_sync_item_efectiva(db, item)
    duplicado, pago_id_exist, prestamo_id_exist = _sync_item_duplicado_en_pagos(
        db, item.numero_referencia, cedula_item
    )

    try:
        nuevo_pe, pe_reutilizado = _pago_con_error_desde_sync_item(db, item)
        _eliminar_filas_gmail_relacionadas(db, item)
        db.commit()
        db.refresh(nuevo_pe)
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception(
            "[PAGOS_GMAIL] migrar_sync_item_a_pendientes: fallo item_id=%s: %s",
            item_id,
            e,
        )
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo migrar la fila a pagos_con_errores: {str(e)[:400]}",
        ) from e

    mensaje = (
        (
            f"Ya existía en pagos_con_errores (pe_id={int(nuevo_pe.id)}); se reutilizó esa fila. "
            if pe_reutilizado
            else f"Fila migrada a pagos_con_errores (pe_id={int(nuevo_pe.id)}). "
        )
        + "Use el modal de revisión manual para validar y aplicar."
    )
    if duplicado:
        mensaje = (
            f"Serial {item.numero_referencia or '(s/r)'} ya existe en cartera "
            f"(pago_id={pago_id_exist}, prestamo_id={prestamo_id_exist}). "
            + (
                f"Ya existía en pagos_con_errores (pe_id={int(nuevo_pe.id)}); "
                if pe_reutilizado
                else f"Fila migrada a pagos_con_errores (pe_id={int(nuevo_pe.id)}); "
            )
            +
            "agregue un código (sufijo) en el modal de revisión manual para resolver el duplicado."
        )

    return {
        "ok": True,
        "movido_a_pagos_con_errores": True,
        "ya_en_pagos": bool(duplicado),
        "pago_id_existente": pago_id_exist if duplicado else None,
        "prestamo_id_existente": prestamo_id_exist if duplicado else None,
        "pago_con_error": _pago_con_error_to_response(nuevo_pe, db),
        "pago_con_error_id": int(nuevo_pe.id),
        "mensaje": mensaje,
    }


class GmailSyncItemEditarBody(BaseModel):
    """Campos editables del sync_item antes de pulsar Guardar.
    Campos no provistos se dejan tal cual están. El backend recorta longitudes a las del modelo.
    """
    banco: Optional[str] = None
    cedula: Optional[str] = None
    fecha_pago: Optional[str] = None  # YYYY-MM-DD o dd/MM/yyyy (mismo parser de gmail_temporal)
    monto: Optional[str] = None
    numero_referencia: Optional[str] = None


@router.put("/sync-items/{item_id}")
def editar_sync_item(
    item_id: int,
    payload: GmailSyncItemEditarBody = Body(...),
    db: Session = Depends(get_db),
):
    """
    Edita campos del `pagos_gmail_sync_item` (y la fila equivalente en `gmail_temporal`).
    Permite corregir extracciones imperfectas de Gemini antes de "Guardar" (que aplica cascada).
    Las validaciones de negocio (FK cliente, duplicado documento, monto>0) siguen ocurriendo en
    el paso Guardar (vía `mover_a_pagos_normales` de `pagos_con_errores`).
    """
    item = db.get(PagosGmailSyncItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"sync_item {item_id} no encontrado")

    cambios: dict[str, str] = {}
    if payload.banco is not None:
        item.banco = (payload.banco or "").strip()[:50] or None
        cambios["banco"] = item.banco or ""
    if payload.cedula is not None:
        item.cedula = (payload.cedula or "").strip()[:50] or None
        cambios["cedula"] = item.cedula or ""
    if payload.fecha_pago is not None:
        item.fecha_pago = (payload.fecha_pago or "").strip()[:100] or None
        cambios["fecha_pago"] = item.fecha_pago or ""
    if payload.monto is not None:
        item.monto = (payload.monto or "").strip()[:100] or None
        cambios["monto"] = item.monto or ""
    if payload.numero_referencia is not None:
        item.numero_referencia = (payload.numero_referencia or "").strip()[:200] or None
        cambios["numero_referencia"] = item.numero_referencia or ""

    # Propagar a gmail_temporal por trazabilidad (cuando exista fila equivalente).
    try:
        if item.gmail_message_id:
            temp_rows = db.execute(
                select(GmailTemporal).where(
                    GmailTemporal.gmail_message_id == item.gmail_message_id
                )
            ).scalars().all()
            for tr in temp_rows:
                if payload.banco is not None:
                    tr.banco = item.banco
                if payload.cedula is not None:
                    tr.cedula = item.cedula
                if payload.fecha_pago is not None:
                    tr.fecha_pago = item.fecha_pago
                if payload.monto is not None:
                    tr.monto = item.monto
                if payload.numero_referencia is not None:
                    tr.numero_referencia = item.numero_referencia
        db.commit()
        db.refresh(item)
    except Exception as e:
        db.rollback()
        logger.exception(
            "[PAGOS_GMAIL] editar_sync_item: fallo item_id=%s: %s", item_id, e
        )
        raise HTTPException(
            status_code=500, detail=f"No se pudo editar: {str(e)[:400]}"
        ) from e

    cedula_item = _cedula_sync_item_efectiva(db, item)
    duplicado, pago_id_exist, prestamo_id_exist = _sync_item_duplicado_en_pagos(
        db, item.numero_referencia, cedula_item
    )
    return {
        "ok": True,
        "item": {
            "id": item.id,
            "banco": item.banco,
            "cedula": cedula_item,
            "fecha_pago": item.fecha_pago,
            "monto": item.monto,
            "numero_referencia": item.numero_referencia,
            "duplicado_en_pagos": duplicado,
            "pago_id_existente": pago_id_exist,
            "prestamo_id_existente": prestamo_id_exist,
        },
        "cambios": cambios,
    }


@router.delete("/sync-items/{item_id}")
def eliminar_sync_item(item_id: int, db: Session = Depends(get_db)):
    """
    Elimina la fila `pagos_gmail_sync_item` (y filas equivalentes en `gmail_temporal`).
    No toca etiquetas Gmail: la regla de skip-por-etiqueta global se preserva.
    Acción local sobre la cola de revisión del módulo.
    """
    item = db.get(PagosGmailSyncItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"sync_item {item_id} no encontrado")
    try:
        eliminados_temporal = _eliminar_filas_gmail_relacionadas(db, item)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception(
            "[PAGOS_GMAIL] eliminar_sync_item: fallo item_id=%s: %s", item_id, e
        )
        raise HTTPException(
            status_code=500, detail=f"No se pudo eliminar: {str(e)[:400]}"
        ) from e
    return {
        "ok": True,
        "sync_item_eliminado": item_id,
        "gmail_temporal_eliminados": eliminados_temporal,
    }


# ---------------------------------------------------------------------------
# Preview (paso 1) y procesar-selección (paso 2) para módulo Actualizaciones > Gmail
# ---------------------------------------------------------------------------


# Preview UI: por defecto se muestran los 20 más recientes; cota dura del listado Gmail = 10000.
_GMAIL_PREVIEW_DEFAULT_RESULTS = 20
_GMAIL_PREVIEW_HARD_CAP = 10000
# Procesar (Gemini) por corrida: por defecto 20, tope 500 para no saturar Gemini ni el lock 2 h.
_GMAIL_PROCESAR_DEFAULT_RESULTS = 20
_GMAIL_PROCESAR_HARD_CAP = 500


def _gmail_user_label_names_for_message(
    user_label_names_by_id: dict[str, str],
    msg_label_ids: list[str],
) -> list[str]:
    """Devuelve los nombres de etiquetas de usuario presentes en el mensaje (orden alfabético)."""
    out = []
    for lid in msg_label_ids:
        nm = user_label_names_by_id.get(lid)
        if nm:
            out.append(nm)
    return sorted(set(out))


@router.get("/preview-remitente")
def preview_remitente(
    correo: str = Query(..., description="Correo a previsualizar (case-insensitive). Por defecto se busca como remitente."),
    max_results: int = Query(
        _GMAIL_PREVIEW_DEFAULT_RESULTS,
        ge=1,
        le=_GMAIL_PREVIEW_HARD_CAP,
        description=(
            "Cuántos mensajes traer al preview (default 20; máximo absoluto 10000). "
            "Gmail siempre filtra por el predicado según `criterio` + criterio media; este "
            "parámetro acota cuántos vienen al UI, no qué se escanea."
        ),
    ),
    criterio: Optional[str] = Query(
        "remitente",
        description=(
            "Cómo aplicar el correo al filtro Gmail: 'remitente' (default, `from:<correo>`); "
            "'destinatario' (`to:<correo>`); 'participante' (`from:<correo> OR to:<correo>`)."
        ),
        pattern="^(remitente|destinatario|participante)$",
    ),
    db: Session = Depends(get_db),
):
    """
    Paso 1 del flujo "re-escaneo selectivo":
    Lista los correos en bandeja que cumplen `from:<correo> + criterio media` SIN escanear
    con Gemini ni descargar binarios. Cruza con `pagos_gmail_sync_item` para indicar cuáles
    ya fueron procesados previamente.

    Coste: una `messages.list` paginada + un `messages.get(format=full)` por mensaje (5 units
    cada uno). No invoca Gemini. Devuelve los datos mínimos para que la UI muestre la lista
    con checkboxes.
    """
    correo_lc = _validate_from_email(correo)
    if not correo_lc:
        raise HTTPException(
            status_code=400,
            detail="Indica un correo válido (ej. cliente@dominio.com).",
        )
    if correo_lc.lower() != PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER:
        raise HTTPException(
            status_code=400,
            detail=(
                f"El módulo Actualizaciones > Gmail solo previsualiza correos de "
                f"'{PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER}'. Remitente recibido: '{correo_lc}'."
            ),
        )

    creds = get_pagos_gmail_credentials()
    if not creds:
        log_pagos_gmail_config_status()
        raise HTTPException(
            status_code=503,
            detail=(
                "Credenciales OAuth inválidas. Vaya a Configuración > Informe de pagos, "
                "reconecte la cuenta Gmail y reintente."
            ),
        )

    from app.services.pagos_gmail.gmail_service import (
        build_gmail_service,
        batch_get_messages_full,
        is_lote_it_master_message,
        list_gmail_user_label_ids,
        pagos_gmail_list_query_for_scan_filter,
        payload_has_media_candidate,
    )

    gmail_svc = build_gmail_service(creds)
    criterio_norm = (criterio or "remitente").strip().lower()
    if criterio_norm not in ("remitente", "destinatario", "participante"):
        criterio_norm = "remitente"
    if correo_lc.lower() == PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER:
        # IT Master es el buzón conectado: buscar en INBOX como destinatario.
        criterio_norm = "destinatario"
    q = pagos_gmail_list_query_for_scan_filter(
        "manual_redigitaliza_por_remitente", correo_lc, criterio=criterio_norm
    )
    logger.info(
        "[PAGOS_GMAIL] preview-remitente q=%r (criterio=%s)", q, criterio_norm
    )

    # Listar IDs del remitente acotado a max_results. Gmail acepta hasta 500 por página;
    # usamos pageSize ajustado para no traer más de lo necesario y ahorrar cuota.
    all_ids: list[str] = []
    page_token: Optional[str] = None
    hay_mas_en_gmail = False
    while True:
        restantes = max_results - len(all_ids)
        if restantes <= 0:
            break
        page_size = min(500, max(1, restantes))
        params: dict = {
            "userId": "me",
            "maxResults": page_size,
            "includeSpamTrash": False,
            "q": q,
        }
        if page_token:
            params["pageToken"] = page_token
        try:
            result = gmail_svc.users().messages().list(**params).execute()
        except Exception as e:
            logger.exception("[PAGOS_GMAIL] preview-remitente list error: %s", e)
            raise HTTPException(
                status_code=502,
                detail=f"Error listando Gmail: {str(e)[:300]}",
            ) from e
        for m in result.get("messages", []):
            all_ids.append(m["id"])
            if len(all_ids) >= max_results:
                break
        page_token = result.get("nextPageToken")
        if not page_token:
            break
        if len(all_ids) >= max_results:
            # Quedaron correos sin traer porque alcanzamos el tope max_results.
            hay_mas_en_gmail = True
            break

    if not all_ids:
        # Diagnóstico extra: contar correos del remitente con menos restricciones para
        # saber si el problema es la query (no hay media), el remitente (no tiene correos),
        # o si el operador esta buscando justamente el correo del propio buzon (caso clasico:
        # los comprobantes los recibe el buzon, no los envia).
        diag_inbox_sin_media = 0
        diag_global = 0
        diag_sent_remitente = 0
        diag_to_remitente = 0
        cuenta_conectada: Optional[str] = None
        try:
            prof = gmail_svc.users().getProfile(userId="me").execute()
            cuenta_conectada = (
                str(prof.get("emailAddress", "") or "").strip().lower() or None
            )
        except Exception as e:
            logger.warning(
                "[PAGOS_GMAIL] preview-remitente diag profile error: %s", e
            )
        try:
            r1 = (
                gmail_svc.users()
                .messages()
                .list(userId="me", maxResults=1, q=f"in:inbox from:{correo_lc}")
                .execute()
            )
            diag_inbox_sin_media = int(r1.get("resultSizeEstimate", 0) or 0)
        except Exception as e:
            logger.warning(
                "[PAGOS_GMAIL] preview-remitente diag inbox-sin-media error: %s", e
            )
        try:
            r2 = (
                gmail_svc.users()
                .messages()
                .list(
                    userId="me",
                    maxResults=1,
                    includeSpamTrash=True,
                    q=f"from:{correo_lc}",
                )
                .execute()
            )
            diag_global = int(r2.get("resultSizeEstimate", 0) or 0)
        except Exception as e:
            logger.warning(
                "[PAGOS_GMAIL] preview-remitente diag global error: %s", e
            )
        try:
            r3 = (
                gmail_svc.users()
                .messages()
                .list(userId="me", maxResults=1, q=f"in:sent from:{correo_lc}")
                .execute()
            )
            diag_sent_remitente = int(r3.get("resultSizeEstimate", 0) or 0)
        except Exception as e:
            logger.warning(
                "[PAGOS_GMAIL] preview-remitente diag sent error: %s", e
            )
        try:
            r4 = (
                gmail_svc.users()
                .messages()
                .list(userId="me", maxResults=1, q=f"in:inbox to:{correo_lc}")
                .execute()
            )
            diag_to_remitente = int(r4.get("resultSizeEstimate", 0) or 0)
        except Exception as e:
            logger.warning(
                "[PAGOS_GMAIL] preview-remitente diag to error: %s", e
            )

        es_la_cuenta_conectada = bool(
            cuenta_conectada and cuenta_conectada == correo_lc
        )

        if es_la_cuenta_conectada:
            mensaje = (
                f"'{correo_lc}' es la propia cuenta Gmail conectada al sistema. "
                "Para el módulo IT Master el sistema busca en INBOX como destinatario "
                f"(`to:{correo_lc}`) y procesa correos con asunto cédula + adjuntos .eml. "
                "Si no aparecen resultados, revise que los correos estén en Bandeja de entrada "
                "de esta cuenta y que tengan adjuntos .eml/message-rfc822."
            )
        elif diag_inbox_sin_media > 0:
            mensaje = (
                f"Gmail tiene ~{diag_inbox_sin_media} correo(s) con 'from:{correo_lc}' en INBOX, "
                "pero ninguno cumple el criterio de adjunto/imagen/PDF "
                "(la query exige has:attachment, filename:eml/msg o filename:png/jpg/jpeg/pdf/webp/heic/gif). "
                "Si los comprobantes están como imágenes inline en el cuerpo, Gmail no los marca "
                "como attachment y son ignorados."
            )
        elif diag_to_remitente > 0:
            mensaje = (
                f"Gmail no encontró correos enviados POR '{correo_lc}', pero sí ~{diag_to_remitente} "
                f"con destinatario 'to:{correo_lc}'. Probablemente está poniendo el correo del "
                "destinatario en lugar del remitente. Use el correo del CLIENTE (quien envía el comprobante)."
            )
        elif diag_global > 0:
            mensaje = (
                f"Gmail encontró ~{diag_global} correo(s) con 'from:{correo_lc}', "
                "pero ninguno está en INBOX (probablemente archivados, en SPAM o en la papelera). "
                "El pipeline solo lee INBOX. Mueva los correos a la bandeja y reintente."
            )
        elif diag_sent_remitente > 0:
            mensaje = (
                f"'{correo_lc}' solo aparece como remitente en la carpeta ENVIADOS "
                f"(~{diag_sent_remitente} correos). El pipeline solo procesa INBOX. Si esos "
                "comprobantes los envió la propia cuenta, no se pueden re-escanear con este flujo."
            )
        else:
            cuenta_txt = (
                f" Cuenta Gmail conectada: {cuenta_conectada}." if cuenta_conectada else ""
            )
            mensaje = (
                f"Gmail no encontró ningún correo con 'from:{correo_lc}'. "
                "Verifique que la dirección esté escrita correctamente y que la cuenta Gmail "
                f"conectada sea la que recibe esos comprobantes.{cuenta_txt}"
            )

        logger.info(
            "[PAGOS_GMAIL] preview-remitente diagnóstico %r (cuenta=%s): "
            "media=0 inbox_sin_media=%d global=%d sent_remitente=%d to_remitente=%d",
            correo_lc,
            cuenta_conectada or "?",
            diag_inbox_sin_media,
            diag_global,
            diag_sent_remitente,
            diag_to_remitente,
        )

        return {
            "correo": correo_lc,
            "total": 0,
            "items": [],
            "max_results": max_results,
            "hard_cap_preview": _GMAIL_PREVIEW_HARD_CAP,
            "procesar_hard_cap": _GMAIL_PROCESAR_HARD_CAP,
            "hay_mas_en_gmail": False,
            "diagnostico_inbox_sin_media": diag_inbox_sin_media,
            "diagnostico_global": diag_global,
            "diagnostico_sent_remitente": diag_sent_remitente,
            "diagnostico_to_remitente": diag_to_remitente,
            "cuenta_conectada": cuenta_conectada,
            "es_la_cuenta_conectada": es_la_cuenta_conectada,
            "mensaje": mensaje,
        }

    # Obtener payload completo en batch (5 units por mensaje en cuota Gmail).
    try:
        meta_by_id = batch_get_messages_full(gmail_svc, all_ids)
    except Exception as e:
        logger.exception("[PAGOS_GMAIL] preview-remitente batch error: %s", e)
        raise HTTPException(
            status_code=502,
            detail=f"Error leyendo Gmail: {str(e)[:300]}",
        ) from e

    user_label_ids_set, user_label_names_by_id, _labels_ok = list_gmail_user_label_ids(gmail_svc)

    # Cruce con BD: marcar mensajes ya procesados por ESTE módulo/correo. Antes se contaba
    # cualquier sync_item con el mismo gmail_message_id, incluso filas viejas creadas con
    # correo_origen distinto (cuando IT Master se trataba como From real). Eso hacía que el
    # preview dijera "ya procesado" pero la tabla fija de itmaster quedara en 0.
    ids_ya_procesados: set[str] = set(
        db.execute(
            select(PagosGmailSyncItem.gmail_message_id)
            .where(
                PagosGmailSyncItem.gmail_message_id.in_(all_ids),
                func.lower(PagosGmailSyncItem.correo_origen) == correo_lc,
            )
        ).scalars().all()
        or []
    )

    items: list[dict] = []
    sender_no_match: int = 0
    sin_media: int = 0
    no_lote_it_master: int = 0

    for mid in all_ids:
        meta = meta_by_id.get(mid)
        if not meta:
            continue
        payload = meta.get("payload", {}) or {}
        headers = {(h.get("name") or "").lower(): h.get("value") or "" for h in payload.get("headers", [])}
        from_h = headers.get("from") or ""
        from_email_real = (extract_sender_email_safe(from_h) or "").strip().lower()
        # Defensa extra para filtros por remitente reales. En IT Master el correo consultado
        # es el buzón receptor (`to:`), por lo que el From real puede ser distinto y NO debe
        # descartarse.
        if correo_lc != PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER and from_email_real != correo_lc:
            sender_no_match += 1
            continue
        subject = (headers.get("subject") or "").strip()
        try:
            internal_date_ms = int(meta.get("internalDate") or 0)
        except (TypeError, ValueError):
            internal_date_ms = 0
        fecha_iso: Optional[str] = None
        if internal_date_ms > 0:
            try:
                fecha_iso = (
                    datetime.utcfromtimestamp(internal_date_ms / 1000.0)
                    .replace(microsecond=0)
                    .isoformat() + "Z"
                )
            except Exception:
                fecha_iso = None
        snippet = (meta.get("snippet") or "").strip()
        label_ids = list(meta.get("labelIds") or [])
        etiquetas_usuario = _gmail_user_label_names_for_message(
            user_label_names_by_id, label_ids
        )
        tiene_media = payload_has_media_candidate(payload)
        if not tiene_media:
            sin_media += 1
        if correo_lc == PAGOS_GMAIL_LOTE_REMITENTE_IT_MASTER:
            es_lote_it_master, _cedula_lote_preview, _n_eml_lote_preview = (
                is_lote_it_master_message(headers, payload)
            )
            if not es_lote_it_master:
                no_lote_it_master += 1
                continue
        thread_id = (meta.get("threadId") or "").strip()
        items.append(
            {
                "gmail_message_id": mid,
                "gmail_thread_id": thread_id or None,
                "fecha_iso": fecha_iso,
                "asunto": subject[:300],
                "snippet": snippet[:300],
                "etiquetas_usuario": etiquetas_usuario,
                "tiene_media": tiene_media,
                "ya_procesado_en_bd": mid in ids_ya_procesados,
                "gmail_url": (
                    f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"
                    if thread_id
                    else None
                ),
            }
        )

    # Orden: más reciente primero (mismo criterio que el pipeline).
    items.sort(key=lambda x: x.get("fecha_iso") or "", reverse=True)

    # Si Gmail devolvió IDs pero la UI queda en 0 (p. ej. por From real distinto al
    # correo consultado), devolvemos también los contadores auxiliares. Antes esos
    # campos solo existían cuando `messages.list` devolvía 0 IDs, por eso el panel
    # mostraba "?" aunque sí había señales útiles para diagnosticar.
    diag_extra: dict = {}
    if not items:
        diag_inbox_sin_media = 0
        diag_global = 0
        diag_sent_remitente = 0
        diag_to_remitente = 0
        cuenta_conectada: Optional[str] = None
        try:
            prof = gmail_svc.users().getProfile(userId="me").execute()
            cuenta_conectada = (
                str(prof.get("emailAddress", "") or "").strip().lower() or None
            )
        except Exception as e:
            logger.warning(
                "[PAGOS_GMAIL] preview-remitente diag profile error (final vacío): %s", e
            )
        try:
            r1 = (
                gmail_svc.users()
                .messages()
                .list(userId="me", maxResults=1, q=f"in:inbox from:{correo_lc}")
                .execute()
            )
            diag_inbox_sin_media = int(r1.get("resultSizeEstimate", 0) or 0)
        except Exception as e:
            logger.warning(
                "[PAGOS_GMAIL] preview-remitente diag inbox-sin-media error (final vacío): %s", e
            )
        try:
            r2 = (
                gmail_svc.users()
                .messages()
                .list(
                    userId="me",
                    maxResults=1,
                    includeSpamTrash=True,
                    q=f"from:{correo_lc}",
                )
                .execute()
            )
            diag_global = int(r2.get("resultSizeEstimate", 0) or 0)
        except Exception as e:
            logger.warning(
                "[PAGOS_GMAIL] preview-remitente diag global error (final vacío): %s", e
            )
        try:
            r3 = (
                gmail_svc.users()
                .messages()
                .list(userId="me", maxResults=1, q=f"in:sent from:{correo_lc}")
                .execute()
            )
            diag_sent_remitente = int(r3.get("resultSizeEstimate", 0) or 0)
        except Exception as e:
            logger.warning(
                "[PAGOS_GMAIL] preview-remitente diag sent error (final vacío): %s", e
            )
        try:
            r4 = (
                gmail_svc.users()
                .messages()
                .list(userId="me", maxResults=1, q=f"in:inbox to:{correo_lc}")
                .execute()
            )
            diag_to_remitente = int(r4.get("resultSizeEstimate", 0) or 0)
        except Exception as e:
            logger.warning(
                "[PAGOS_GMAIL] preview-remitente diag to error (final vacío): %s", e
            )

        if no_lote_it_master > 0:
            mensaje = (
                f"Gmail devolvió {len(all_ids)} mensaje(s), pero {no_lote_it_master} "
                "no cumplen el formato del lote IT Master: asunto numérico de cédula "
                "y al menos un adjunto .eml/message-rfc822. Esos mensajes se omiten sin Gemini."
            )
        elif sender_no_match > 0:
            mensaje = (
                f"Gmail devolvió {len(all_ids)} mensaje(s) con la query, pero {sender_no_match} "
                f"fueron descartados porque el header From real no coincide exactamente con "
                f"'{correo_lc}'. Revise el remitente real del correo IT Master en Gmail."
            )
        elif sin_media > 0:
            mensaje = (
                f"Gmail devolvió {len(all_ids)} mensaje(s), pero {sin_media} no exponen "
                "adjuntos compatibles al leer el payload (se esperan .eml/message-rfc822 o imagen/PDF)."
            )
        else:
            mensaje = (
                f"Gmail devolvió {len(all_ids)} mensaje(s), pero ninguno quedó visible en el preview. "
                "Revise logs backend para ids_remitente_no_coincide / ids_sin_media."
            )

        diag_extra = {
            "diagnostico_inbox_sin_media": diag_inbox_sin_media,
            "diagnostico_global": diag_global,
            "diagnostico_sent_remitente": diag_sent_remitente,
            "diagnostico_to_remitente": diag_to_remitente,
            "cuenta_conectada": cuenta_conectada,
            "es_la_cuenta_conectada": bool(
                cuenta_conectada and cuenta_conectada == correo_lc
            ),
            "mensaje": mensaje,
        }

    return {
        "correo": correo_lc,
        "total": len(items),
        "items": items,
        "ids_total_listados_gmail": len(all_ids),
        "hay_mas_en_gmail": hay_mas_en_gmail,
        "max_results": max_results,
        "hard_cap_preview": _GMAIL_PREVIEW_HARD_CAP,
        "procesar_hard_cap": _GMAIL_PROCESAR_HARD_CAP,
        "ids_remitente_no_coincide": sender_no_match,
        "ids_sin_media": sin_media,
        "ids_no_lote_it_master": no_lote_it_master,
        "labels_catalog_ok": _labels_ok,
        **diag_extra,
    }


def extract_sender_email_safe(from_h: str) -> Optional[str]:
    """Wrapper que evita importar la helper dentro del endpoint cada vez."""
    from app.services.pagos_gmail.helpers import extract_sender_email
    try:
        return extract_sender_email(from_h or "")
    except Exception:
        return None


class GmailProcesarMensajesBody(BaseModel):
    correo: str
    mensajes_ids: list[str]


@router.post("/procesar-mensajes")
def procesar_mensajes(
    background_tasks: BackgroundTasks,
    payload: GmailProcesarMensajesBody = Body(...),
    db: Session = Depends(get_db),
):
    """
    Paso 2 del flujo "re-escaneo selectivo":
    Lanza el pipeline acotado a los `mensajes_ids` indicados (todos del remitente `correo`).
    El pipeline NO llama a `messages.list`: procesa exactamente esos IDs con todo el flujo
    vigente (Gemini -> plantillas A-F -> BD -> cascada de cuotas -> etiqueta final).

    Reusa la misma cola/lock global de 2 h y devuelve `sync_id` para que la UI haga polling
    a `/pagos/gmail/status`.
    """
    correo_lc = _validate_from_email(payload.correo)
    if not correo_lc:
        raise HTTPException(
            status_code=400,
            detail="Indica un correo válido (ej. cliente@dominio.com).",
        )
    ids = [str(m).strip() for m in (payload.mensajes_ids or []) if str(m).strip()]
    if not ids:
        raise HTTPException(
            status_code=400,
            detail="Indica al menos un gmail_message_id en 'mensajes_ids'.",
        )
    if len(ids) > _GMAIL_PROCESAR_HARD_CAP:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Demasiados mensajes en una sola corrida (máx {_GMAIL_PROCESAR_HARD_CAP}). "
                "Divide la selección en varias pasadas."
            ),
        )

    blocking = _get_blocking_running_sync(db)
    if blocking is not None:
        started = blocking.started_at.isoformat() if blocking.started_at else "?"
        raise HTTPException(
            status_code=409,
            detail=(
                f"Ya hay una sincronización en curso (sync_id={blocking.id}, iniciada={started}). "
                "Espere a que termine."
            ),
        )

    creds = get_pagos_gmail_credentials()
    if not creds:
        log_pagos_gmail_config_status()
        raise HTTPException(
            status_code=503,
            detail="Credenciales OAuth inválidas. Reconecte la cuenta Gmail y reintente.",
        )

    # Defensa: validamos que cada ID corresponde realmente al remitente indicado.
    from app.services.pagos_gmail.gmail_service import (
        build_gmail_service,
        batch_get_messages_metadata,
    )
    gmail_svc = build_gmail_service(creds)
    try:
        meta_by_id = batch_get_messages_metadata(
            gmail_svc, ids, metadata_headers=["From"]
        )
    except Exception as e:
        logger.exception("[PAGOS_GMAIL] procesar-mensajes metadata error: %s", e)
        raise HTTPException(
            status_code=502, detail=f"Error verificando Gmail: {str(e)[:300]}"
        ) from e

    ids_validos: list[str] = []
    ids_remitente_distinto: list[str] = []
    ids_inexistentes: list[str] = []
    for mid in ids:
        meta = meta_by_id.get(mid)
        if not meta:
            ids_inexistentes.append(mid)
            continue
        payload_meta = meta.get("payload", {}) or {}
        headers = {(h.get("name") or "").lower(): h.get("value") or "" for h in payload_meta.get("headers", [])}
        from_h = headers.get("from") or ""
        from_real = (extract_sender_email_safe(from_h) or "").strip().lower()
        if from_real != correo_lc:
            ids_remitente_distinto.append(mid)
            continue
        ids_validos.append(mid)

    if not ids_validos:
        raise HTTPException(
            status_code=400,
            detail=(
                "Ninguno de los IDs indicados corresponde al remitente '"
                + correo_lc
                + f"'. inexistentes={len(ids_inexistentes)}, otro_remitente={len(ids_remitente_distinto)}"
            ),
        )

    # Crear sync_id de inmediato (evita doble click).
    sync = PagosGmailSync(status="running", emails_processed=0, files_processed=0)
    db.add(sync)
    db.commit()
    db.refresh(sync)
    sync_id = sync.id

    background_tasks.add_task(
        _run_pipeline_background,
        sync_id,
        "manual_redigitaliza_por_remitente",
        correo_lc,
        ids_validos,
    )
    return {
        "sync_id": sync_id,
        "status": "running",
        "scan_filter": "manual_redigitaliza_por_remitente",
        "from_email": correo_lc,
        "mensajes_a_procesar": len(ids_validos),
        "ids_remitente_distinto": ids_remitente_distinto,
        "ids_inexistentes": ids_inexistentes,
    }
