"""
Scheduler para tareas programadas (zona America/Caracas).

Solo se registra e inicia si en el arranque ENABLE_AUTOMATIC_SCHEDULED_JOBS=true en settings (.env).
Por defecto esta desactivado: ningun cron en servidor; la pantalla Configuracion no dispara estos jobs.

Cuando esta activo:
- todos los dias 01:00  Clientes (Drive): sync A:S, caché candidatos + import automático filas seleccionable (ENABLE_DRIVE_CLIENTES_NIGHTLY_0100 / AUTO_GUARDAR).
- todos los dias 02:00  Préstamos Drive: sync A:S, snapshot candidatos + guardar automático al 100% (ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY / AUTO_GUARDAR).
- 03:00  Auditoria cartera: evaluacion de prestamos y metadatos en configuracion.
- 04:00  Limpieza codigos estado de cuenta.
- todos los dias 04:05  Caché lista «Clientes (Drive)» solo recalculo (respaldo tras auditoría).
- todos los dias 04:45  Snapshot candidatos préstamo solo recalculo.
- Gmail sin etiqueta de usuario (America/Caracas, si PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED=true):
  lun-dom en horarios fijos PAGOS_GMAIL_SCAN_SLOTS (defecto 04:30, 08:00, 11:00, 16:30, 20:30).
- Auditoría Email: si AUDITORIA_EMAIL_AUTO_ADVANCE_ENABLED, interval (defecto 5 min) reanuda
  escaneos paused con pageToken (batch cobranza@ sin depender del navegador).
- lun-vie America/Caracas: bot de un GET al recuadro USD de bcv.org.ve (si ENABLE_BCV_WIDGET_TASA_JOB=true)
  a las 08:30 (recupero), 16:00, 16:30, 17:00, 17:30, 18:00 y 18:30. El BCV publica la tasa del
  siguiente día hábil en la tarde (~16:00–18:30 Caracas; el viernes cubre el lunes). Si ya hay
  tasa_bcv para ese día hábil siguiente, el job no vuelve a pegarle a la portada.
- Recibos (correo estado de cuenta tras pagos conciliados): manual (POST /notificaciones/recibos/ejecutar) y,
  si ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS, cron lun-dom en RECIBOS_CRON_SLOTS Caracas
  (defecto 05:00, 11:50, 17:00, 21:00; lote hasta RECIBOS_BATCH_MAX salvo 21:00 sin tope).
- Opcional: envío automático PREJUDICIAL / a-2-cuotas si ENABLE_CRON_NOTIFICACIONES_PREJUDICIAL
  (defecto **02:22** Caracas, lun–dom).
- Opcional: envío automático atraso-10-dias (PAGO_10_DIAS_ATRASADO) si ENABLE_CRON_NOTIFICACIONES_ATRASO_10_DIAS
  (defecto **02:40** Caracas, lun–dom).
- Opcional: «2 días antes» y «día siguiente» si ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES /
  ENABLE_CRON_NOTIFICACIONES_DIA_SIGUIENTE (madrugada + tarde según CRON_*_SLOTS).
- Opcional: envío automático Estado de cuenta (ESTADO_CUENTA) si ENABLE_CRON_NOTIFICACIONES_ESTADO_CUENTA
  (defecto CRON_ESTADO_CUENTA_SLOTS 03:28 y 04:12 Caracas).

- Reportes cobranzas, informe de pagos por email y campanas CRM: manual o bajo demanda.
- Finiquito: sin cron; refresco manual (API/UI) y/o al liquidar por pago.
- todos los dias 18:00  Gestores cobranza: 9 Excel a operaciones@ (BCC itmaster@) + snapshot
  dashboard, si ENABLE_COBRANZA_GESTORES_EMAIL_JOB (requiere ENABLE_AUTOMATIC_SCHEDULED_JOBS).

Criterios al cambiar horarios (carga, colisiones, dependencias): comentarios en este módulo y Field descriptions en Settings.
"""
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.combining import OrTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

# Zona horaria por defecto (Venezuela). Configurable vÃ­a env si se aÃ±ade SCHEDULER_TZ.
SCHEDULER_TZ = "America/Caracas"

# Complejidad aproximada (duración / carga BD) — guía al espaciar triggers y evitar el mismo minuto:
#   Medio: snapshot prestamo_candidatos_drive, caché clientes Drive.
#   Ligero: limpieza estado_cuenta_codigos.
# Jobs clientes/prestamos Drive leen tabla `drive` en BD (04:05 / 04:45 recalculan sin Google Sheets).
# El pool del scheduler usa 1 hilo: ningún job se solapa con otro (evita colisiones DB/API).

# Gmail programado: horarios fijos America/Caracas (lun-dom).
PAGOS_GMAIL_SCAN_TIMES: tuple[tuple[int, int], ...] = (
    (4, 30),
    (8, 0),
    (11, 0),
    (16, 30),
    (20, 30),
)
PAGOS_GMAIL_PENDING_SCAN_JOB_ID = "pagos_gmail_pending_scan_caracas"
AUDITORIA_EMAIL_AUTO_ADVANCE_JOB_ID = "auditoria_email_auto_advance"
# Recibos programados: horarios fijos Caracas (lun-dom).
RECIBOS_CRON_TIMES: tuple[tuple[int, int], ...] = (
    (5, 0),
    (11, 50),
    (17, 0),
    (21, 0),
)
RECIBOS_CRON_JOB_PREFIX = "recibos_conciliacion_email"
RECIBOS_CONCILIACION_EMAIL_JOB_ID = "recibos_conciliacion_email_diario"
ESTADO_CUENTA_EMAIL_JOB_ID = "notificaciones_estado_cuenta_diario"
ESTADO_CUENTA_CRON_JOB_PREFIX = "notificaciones_estado_cuenta"
PREJUDICIAL_2_CUOTAS_EMAIL_JOB_ID = "notificaciones_prejudicial_2_cuotas_diario"
ATRASO_10_DIAS_EMAIL_JOB_ID = "notificaciones_atraso_10_dias_diario"
DIA_SIGUIENTE_EMAIL_JOB_ID = "notificaciones_dia_siguiente_diario"
CRON_2_DIAS_JOB_PREFIX = "notificaciones_pago_2_dias_antes"
CRON_DIA_SIGUIENTE_JOB_PREFIX = "notificaciones_dia_siguiente"
BCV_WIDGET_TASA_JOB_ID = "bcv_widget_tasa_caracas"
COBROS_RECONCILIAR_DAY_SLOTS: tuple[tuple[int, int], ...] = (
    (8, 0),
    (8, 45),
    (9, 30),
    (10, 15),
    (11, 0),
    (11, 45),
    (12, 30),
    (13, 15),
    (14, 0),
    (14, 45),
    (15, 30),
    (16, 15),
    (17, 0),
    (17, 45),
    (18, 30),
    (19, 15),
    (20, 0),
)
COBROS_RECONCILIAR_OFFHOURS_SLOTS: tuple[tuple[int, int], ...] = (
    (0, 0),
    (2, 0),
    (4, 0),
    (6, 0),
    (22, 0),
    (23, 0),
)
# BCV no publica hora oficial. En días hábiles la tasa con fecha valor = siguiente
# hábil suele salir entre ~16:00 y 18:30 Caracas (viernes → lunes). 08:30 recupera
# si el recuadro de ayer no se pudo leer (WAF/red).
BCV_WIDGET_TASA_TIMES: tuple[tuple[int, int], ...] = (
    (8, 30),
    (16, 0),
    (16, 30),
    (17, 0),
    (17, 30),
    (18, 0),
    (18, 30),
)
BCV_WIDGET_TASA_DAYS = "mon-fri"


def _parse_hhmm_slots(raw: str, default: tuple[tuple[int, int], ...]) -> tuple[tuple[int, int], ...]:
    out: List[Tuple[int, int]] = []
    seen: set[Tuple[int, int]] = set()
    for part in str(raw or "").split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        h_s, m_s = part.split(":", 1)
        try:
            h = max(0, min(23, int(h_s.strip())))
            m = max(0, min(59, int(m_s.strip())))
        except ValueError:
            continue
        key = (h, m)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return tuple(out) if out else default


def _cron_slots_label(slots: tuple[tuple[int, int], ...]) -> str:
    return ", ".join(f"{h:02d}:{m:02d}" for h, m in slots)


def _cron_slots_or_trigger(
    slots: tuple[tuple[int, int], ...],
    *,
    day_of_week: str = "sun,mon,tue,wed,thu,fri,sat",
) -> OrTrigger:
    return OrTrigger(
        [
            CronTrigger(
                day_of_week=day_of_week,
                hour=h,
                minute=m,
                timezone=SCHEDULER_TZ,
            )
            for h, m in slots
        ]
    )


def _pagos_gmail_scan_times() -> tuple[tuple[int, int], ...]:
    raw = getattr(settings, "PAGOS_GMAIL_SCAN_SLOTS", None)
    if raw and str(raw).strip():
        return _parse_hhmm_slots(str(raw), PAGOS_GMAIL_SCAN_TIMES)
    return PAGOS_GMAIL_SCAN_TIMES


def _pagos_gmail_scan_times_label() -> str:
    return f"lun-dom {_cron_slots_label(_pagos_gmail_scan_times())} (Caracas)"


def _pagos_gmail_scan_or_trigger() -> OrTrigger:
    return _cron_slots_or_trigger(_pagos_gmail_scan_times())


def _recibos_cron_times() -> tuple[tuple[int, int], ...]:
    raw = getattr(settings, "RECIBOS_CRON_SLOTS", None)
    if raw and str(raw).strip():
        return _parse_hhmm_slots(str(raw), RECIBOS_CRON_TIMES)
    return RECIBOS_CRON_TIMES


def _recibos_cron_times_label() -> str:
    return f"lun-dom {_cron_slots_label(_recibos_cron_times())} (Caracas)"


def _estado_cuenta_cron_times() -> tuple[tuple[int, int], ...]:
    raw = getattr(settings, "CRON_ESTADO_CUENTA_SLOTS", None)
    if raw and str(raw).strip():
        return _parse_hhmm_slots(str(raw), ((3, 28), (4, 12)))
    h = int(getattr(settings, "CRON_ESTADO_CUENTA_HOUR", 3) or 3)
    m = int(getattr(settings, "CRON_ESTADO_CUENTA_MINUTE", 28) or 28)
    end_h = int(getattr(settings, "CRON_ESTADO_CUENTA_CATCHUP_HOUR_END", 4) or 4)
    h = max(0, min(23, h))
    m = max(0, min(59, m))
    end_h = max(h, min(23, end_h))
    if end_h == h:
        return ((h, m),)
    return ((h, m), (end_h, m))


def _recibos_batch_max() -> int:
    try:
        n = int(getattr(settings, "RECIBOS_BATCH_MAX", 100) or 100)
    except (TypeError, ValueError):
        n = 100
    return max(1, min(n, 500))


_scheduler: Optional[BackgroundScheduler] = None


@contextmanager
def _scheduler_job_span(job_id: str):
    """Mide duración de un job programado (logs job_start / job_end con duration_ms)."""
    t0 = time.perf_counter()
    logger.info("[scheduler] job_start id=%s", job_id)
    try:
        yield
    finally:
        ms = int((time.perf_counter() - t0) * 1000)
        logger.info("[scheduler] job_end id=%s duration_ms=%s", job_id, ms)


def _wrap_job_with_timing(job_id: str, fn: Callable[[], None]) -> Callable[[], None]:
    def _wrapped() -> None:
        with _scheduler_job_span(job_id):
            fn()

    return _wrapped


def get_pagos_gmail_scan_next_run_iso() -> Optional[str]:
    """Proxima ejecucion ISO8601 del job Gmail programado, o None si no hay scheduler o el job no esta registrado."""
    if _scheduler is None:
        return None
    job = _scheduler.get_job(PAGOS_GMAIL_PENDING_SCAN_JOB_ID)
    if job is None or job.next_run_time is None:
        return None
    return job.next_run_time.isoformat()


def scheduler_is_running() -> bool:
    """True si este proceso ya tiene BackgroundScheduler iniciado (lider con jobs registrados)."""
    return _scheduler is not None


def _job_cobranza_gestores_email_1800() -> None:
    """Todos los dias 18:00–21:00 Caracas: 9 Excel a operaciones@ (idempotente por dia)."""
    db = SessionLocal()
    try:
        from app.services.cobranzas.gestores_email_diario_job import (
            ejecutar_gestores_email_cron,
        )

        res = ejecutar_gestores_email_cron(db, origen="cron")
        logger.info(
            "[gestores] job email ok=%s omitido=%s adjuntos=%s asunto=%s error=%s motivo=%s",
            res.get("ok"),
            res.get("omitido"),
            res.get("adjuntos"),
            res.get("asunto"),
            res.get("error"),
            res.get("motivo"),
        )
    except Exception as e:
        logger.exception("Error en job cobranza_gestores_email_1800: %s", e)
    finally:
        db.close()


def _job_auditoria_cartera_prestamos() -> None:
    """Job 03:00. Evalua prestamos (cartera), alinea cuotas.estado con reglas, persiste metadatos en configuracion."""
    db = SessionLocal()
    try:
        from app.services.cuota_estado import sincronizar_estado_cuotas_cartera
        from app.services.prestamo_cartera_auditoria import ejecutar_auditoria_cartera, persistir_meta_ejecucion

        sync = sincronizar_estado_cuotas_cartera(db, commit=True)
        _rows, resumen = ejecutar_auditoria_cartera(
            db,
            solo_con_alerta=False,
            skip=0,
            limit=None,
            incluir_filas=False,
            excluir_marcar_ok=False,
            codigo_control=None,
        )
        persistir_meta_ejecucion(
            db,
            total_evaluados=int(resumen.get("prestamos_evaluados") or 0),
            con_alerta=int(resumen.get("prestamos_con_alerta") or 0),
            conteos_por_control=resumen.get("conteos_por_control")
            if isinstance(resumen.get("conteos_por_control"), dict)
            else None,
            reglas_version=str(resumen.get("reglas_version") or ""),
            commit=True,
        )
        logger.info(
            "Auditoria cartera prestamos: evaluados=%s con_alerta=%s; sync_estado cuotas escaneadas=%s actualizadas=%s",
            resumen.get("prestamos_evaluados"),
            resumen.get("prestamos_con_alerta"),
            sync.get("cuotas_escaneadas"),
            sync.get("estados_actualizados"),
        )
    except Exception as e:
        logger.exception("Error en job auditoria_cartera_prestamos: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()


def _job_drive_clientes_noche_0100() -> None:
    """01:00 Caracas: sync A:S hasta cola real, caché; importa automático filas seleccionable (resto en pantalla)."""
    if not getattr(settings, "ENABLE_DRIVE_CLIENTES_NIGHTLY_0100", True):
        return
    db = SessionLocal()
    try:
        from app.core.scheduler_jobs_user import email_usuario_para_job_scheduler
        from app.services.cliente_alta_desde_drive_service import (
            ejecutar_importar_candidatos_drive_seleccionables_automatico,
            refrescar_cache_candidatos_drive,
        )
        from app.services.conciliacion_sheet_sync import run_sync_to_db

        res = run_sync_to_db(db)

        guardar_res: Dict[str, Any] = {}
        if getattr(settings, "ENABLE_DRIVE_CLIENTES_AUTO_GUARDAR_NIGHTLY", True):
            guardar_res = ejecutar_importar_candidatos_drive_seleccionables_automatico(
                db,
                usuario_email=email_usuario_para_job_scheduler(),
            )

        cache = refrescar_cache_candidatos_drive(db)
        logger.info(
            "[drive_clientes_0100] OK filas=%s ultima_fila_a=%s candidatos_pantalla=%s auto_import=%s",
            res.get("row_count"),
            res.get("column_a_last_row"),
            cache.get("total_candidatos"),
            guardar_res,
        )
    except ValueError as e:
        logger.warning("[drive_clientes_0100] omitido: %s", e)
    except Exception as e:
        logger.exception("[drive_clientes_0100] error: %s", e)
    finally:
        db.close()


def _job_prestamo_candidatos_noche_0200() -> None:
    """02:00 Caracas: sync A:S, snapshot; guarda automático filas al 100% (resto en pantalla)."""
    if not getattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY", True):
        return
    db = SessionLocal()
    try:
        from app.core.scheduler_jobs_user import usuario_respuesta_para_job_scheduler
        from app.services.conciliacion_sheet_sync import run_sync_to_db
        from app.services.prestamo_candidatos_drive_guardar import (
            ejecutar_guardar_candidatos_drive_validados_100,
        )
        from app.services.prestamo_candidatos_drive_job import (
            ejecutar_refresh_prestamo_candidatos_drive,
        )

        sync_res = run_sync_to_db(db)
        refresh_res = ejecutar_refresh_prestamo_candidatos_drive(db)

        guardar_res: Dict[str, Any] = {}
        if getattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_AUTO_GUARDAR_NIGHTLY", True):
            guardar_res = ejecutar_guardar_candidatos_drive_validados_100(
                db, current_user=usuario_respuesta_para_job_scheduler(db)
            )

        logger.info(
            "[prestamo_candidatos_0200] OK sync_filas=%s ultima_fila_a=%s snapshot=%s guardar=%s",
            sync_res.get("row_count"),
            sync_res.get("column_a_last_row"),
            refresh_res.get("candidatos_insertados"),
            guardar_res,
        )
    except ValueError as e:
        logger.warning("[prestamo_candidatos_0200] omitido: %s", e)
    except Exception as e:
        logger.exception("[prestamo_candidatos_0200] error: %s", e)
    finally:
        db.close()


def _job_prestamo_candidatos_drive_refresh() -> None:
    """04:45 Caracas: solo recalcula prestamo_candidatos_drive desde `drive` (sin Google Sheets)."""
    if not getattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY", True):
        return
    db = SessionLocal()
    try:
        from app.services.prestamo_candidatos_drive_job import (
            ejecutar_refresh_prestamo_candidatos_drive,
        )

        res = ejecutar_refresh_prestamo_candidatos_drive(db)
        logger.info(
            "[prestamo_candidatos_drive] programado ok insertados=%s filas_drive=%s",
            res.get("candidatos_insertados"),
            res.get("filas_en_drive"),
        )
    except Exception as e:
        logger.exception("[prestamo_candidatos_drive] programado error: %s", e)
    finally:
        db.close()


def _job_drive_clientes_candidatos_cache() -> None:
    """04:05 Caracas: solo recalcula drive_clientes_candidatos_cache."""
    db = SessionLocal()
    try:
        from app.services.cliente_alta_desde_drive_service import refrescar_cache_candidatos_drive

        res = refrescar_cache_candidatos_drive(db)
        logger.info(
            "[drive_clientes_candidatos_cache] job programado OK total=%s drive_synced_at=%s computed_at=%s",
            res.get("total_candidatos"),
            res.get("drive_synced_at"),
            res.get("computed_at"),
        )
    except Exception as e:
        logger.exception("[drive_clientes_candidatos_cache] job programado error: %s", e)
    finally:
        db.close()


def _job_limpiar_estado_cuenta_codigos() -> None:
    """Job 4:00. Borra cÃ³digos de estado de cuenta expirados o usados hace mÃ¡s de 24 h."""
    db = SessionLocal()
    try:
        from app.services.estado_cuenta_cleanup import limpiar_estado_cuenta_codigos
        result = limpiar_estado_cuenta_codigos(db)
        logger.info("Limpieza estado_cuenta_codigos: borrados=%s", result.get("borrados", 0))
    except Exception as e:
        logger.exception("Error en job limpiar_estado_cuenta_codigos: %s", e)
    finally:
        db.close()


def _job_pagos_gmail_pending_scan() -> None:
    """Horarios fijos America/Caracas: mismo pipeline que «Procesar manualmente», solo correos sin etiqueta de usuario."""
    if not getattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", False):
        return
    db = SessionLocal()
    try:
        from app.services.pagos_gmail.runner import schedule_gmail_pipeline_background
        from app.services.pagos_gmail.sync_stale import (
            GmailPipelineBusyError,
            reconcile_blocking_running_gmail_sync_if_stale,
            reserve_gmail_pipeline_sync,
        )

        reconcile_blocking_running_gmail_sync_if_stale(db)
        try:
            sync = reserve_gmail_pipeline_sync(db, force=False)
        except GmailPipelineBusyError:
            logger.info("[PAGOS_GMAIL] Escaneo programado omitido: sync en curso")
            return
        logger.info(
            "[PAGOS_GMAIL] Escaneo programado: pending_identification (sin etiqueta de usuario) sync_id=%s",
            sync.id,
        )
        schedule_gmail_pipeline_background(sync.id, scan_filter="pending_identification")
    except Exception as e:
        logger.exception("[PAGOS_GMAIL] Escaneo programado: %s", e)
    finally:
        db.close()


def _job_auditoria_email_auto_advance() -> None:
    """Intervalo: reanuda escaneos Auditoría Email paused con pageToken."""
    if not getattr(settings, "AUDITORIA_EMAIL_AUTO_ADVANCE_ENABLED", False):
        return
    db = SessionLocal()
    try:
        from app.services.auditoria_email.scan_service import auto_advance_paused_scans

        out = auto_advance_paused_scans(db, max_scans=1)
        advanced = out.get("advanced") or []
        if advanced:
            logger.info("[AUDITORIA_EMAIL] auto-avance: %s", out)
        elif not out.get("ok"):
            logger.info("[AUDITORIA_EMAIL] auto-avance omitido: %s", out.get("reason"))
    except Exception as e:
        logger.exception("[AUDITORIA_EMAIL] auto-avance: %s", e)
    finally:
        db.close()


def _bcv_widget_tasa_times_label() -> str:
    return ", ".join(f"{h:02d}:{m:02d}" for h, m in BCV_WIDGET_TASA_TIMES)


def _bcv_widget_tasa_or_trigger() -> OrTrigger:
    return OrTrigger(
        [
            CronTrigger(
                day_of_week=BCV_WIDGET_TASA_DAYS,
                hour=h,
                minute=m,
                timezone=SCHEDULER_TZ,
            )
            for h, m in BCV_WIDGET_TASA_TIMES
        ]
    )


def _job_bcv_widget_tasa() -> None:
    """Lun-vie Caracas: GET al recuadro USD (fecha valor = siguiente hábil)."""
    if not getattr(settings, "ENABLE_BCV_WIDGET_TASA_JOB", False):
        return
    from app.services.bcv_widget_tasa_service import (
        BcvWidgetTasaError,
        intentar_captura_bcv_desde_widget,
    )

    db = SessionLocal()
    try:
        result = intentar_captura_bcv_desde_widget(db)
        if result.get("omitido"):
            logger.info("[BCV_WIDGET] omitido: %s", result.get("razon") or result.get("mensaje"))
            return
        logger.info("[BCV_WIDGET] sync ok %s", result)
    except BcvWidgetTasaError as e:
        logger.warning("[BCV_WIDGET] no se pudo leer el recuadro: %s", e)
    except Exception as e:
        logger.exception("[BCV_WIDGET] escaneo programado: %s", e)
    finally:
        db.close()


def _job_notificaciones_pago_2_dias_antes_cron() -> None:
    """Cron diario «2 días antes» (PAGO_2_DIAS_ANTES_PENDIENTE) America/Caracas."""
    from app.services.notificaciones_cron_2_dias_antes_job import (
        job_cron_pago_2_dias_antes_scheduler,
    )

    job_cron_pago_2_dias_antes_scheduler()


def _job_notificaciones_prejudicial_2_cuotas_cron() -> None:
    """Cron diario PREJUDICIAL / a-2-cuotas (00:20 Caracas por defecto, lun–dom)."""
    from app.services.notificaciones_cron_prejudicial_2_cuotas_job import (
        job_cron_prejudicial_2_cuotas_scheduler,
    )

    job_cron_prejudicial_2_cuotas_scheduler()


def _job_notificaciones_atraso_10_dias_cron() -> None:
    """Cron diario atraso-10-dias / PAGO_10_DIAS_ATRASADO (13:15 Caracas por defecto, lun–dom)."""
    from app.services.notificaciones_cron_atraso_10_dias_job import (
        job_cron_atraso_10_dias_scheduler,
    )

    job_cron_atraso_10_dias_scheduler()


def _job_notificaciones_dia_siguiente_cron() -> None:
    """Cron PAGO_1_DIA_ATRASADO / día siguiente (09:15 y 17:15 Caracas por defecto, lun–dom)."""
    from app.services.notificaciones_cron_dia_siguiente_job import (
        job_cron_dia_siguiente_scheduler,
    )

    job_cron_dia_siguiente_scheduler()


def _job_cobros_reconciliar_reportados_cartera() -> None:
    """Marca importado reportes cuyo comprobante ya existe en pagos (anti-huerfanos)."""
    db = SessionLocal()
    try:
        from app.api.v1.endpoints.cobros.reportados_validadores_helpers import (
            _reconciliar_reportados_ya_en_cartera,
        )

        n = _reconciliar_reportados_ya_en_cartera(db, max_ids=400)
        if n:
            logger.info("[cobros] reconciliar reportados cartera: %s marcados importado", n)
    except Exception as e:
        logger.exception("[cobros] reconciliar reportados cartera: %s", e)
    finally:
        db.close()


def _job_cobros_sanear_aprobado_limbo(*, barrido_fuerte: bool = False) -> None:
    """Drena limbo aprobado + recupera en_revision current_user + Gmail traza + purge."""
    db = SessionLocal()
    try:
        from app.services.cobros.saneamiento_aprobado_limbo import (
            sanear_aprobados_en_limbo,
            sanear_en_revision_recuperables,
            sanear_importados_sin_cartera_aplicada,
        )

        max_lote = 400 if barrido_fuerte else 120
        # Oldest-first para drenar backlog histórico; lotes acotados por ciclo.
        res = sanear_aprobados_en_limbo(
            db,
            max_ids=max_lote,
            dry_run=False,
            oldest_first=True,
            include_detalle=False,
        )
        if res.scanned:
            logger.info(
                "[cobros] saneamiento limbo aprobado: scanned=%s colision=%s "
                "import_auto=%s revision=%s errores=%s",
                res.scanned,
                res.marcado_importado_colision,
                res.importado_auto,
                res.a_en_revision,
                res.errores,
            )
        fant_rev = 0
        try:
            after_id = 0
            for _loop in range(2):
                fant = sanear_importados_sin_cartera_aplicada(
                    db,
                    max_ids=150,
                    dry_run=False,
                    oldest_first=True,
                    include_detalle=False,
                    after_id=after_id,
                )
                fant_rev += int(fant.a_en_revision or 0)
                after_id = int(fant.last_id or after_id)
                if int(fant.scanned or 0) == 0:
                    break
            if fant_rev:
                logger.info(
                    "[cobros] saneamiento importado fantasma: revision=%s last_id=%s",
                    fant_rev,
                    after_id,
                )
                try:
                    from app.api.v1.endpoints.cobros.listado_kpis_cache import (
                        _invalidate_cobros_listado_kpis_cache,
                    )

                    _invalidate_cobros_listado_kpis_cache()
                except Exception:
                    pass
        except Exception as fant_err:
            logger.warning("[cobros] saneamiento importado fantasma: %s", fant_err)
        try:
            rev = sanear_en_revision_recuperables(
                db,
                max_ids=80,
                dry_run=False,
                include_detalle=False,
                solo_bug_current_user=True,
            )
            if rev.scanned:
                logger.info(
                    "[cobros] saneamiento en_revision recuperables: %s",
                    rev.as_dict(),
                )
        except Exception as rev_err:
            logger.warning("[cobros] saneamiento en_revision: %s", rev_err)
        try:
            from app.services.pagos_gmail.gmail_abcd_cuotas_traza import (
                reconciliar_cuotas_ok_sin_pago_id,
            )

            gmail_rec = reconciliar_cuotas_ok_sin_pago_id(
                db, max_ids=250, dry_run=False
            )
            if gmail_rec.get("linked"):
                logger.info("[cobros] gmail traza reconciliar: %s", gmail_rec)
        except Exception as gmail_err:
            logger.warning("[cobros] gmail traza reconciliar: %s", gmail_err)
        try:
            from app.services.cobros.infopagos_escaner_borrador_service import (
                purgar_borradores_huerfanos_antiguos,
            )

            purge = purgar_borradores_huerfanos_antiguos(
                db, older_than_days=7, max_rows=400, dry_run=False
            )
            if purge.get("eliminados"):
                logger.info("[cobros] purge borradores Infopagos: %s", purge)
            # Segunda pasada más agresiva (3d) para vaciar backlog abandonado.
            purge_fast = purgar_borradores_huerfanos_antiguos(
                db, older_than_days=3, max_rows=200, dry_run=False
            )
            if purge_fast.get("eliminados"):
                logger.info(
                    "[cobros] purge borradores Infopagos (3d): %s", purge_fast
                )
        except Exception as purge_err:
            logger.warning("[cobros] purge borradores: %s", purge_err)
        try:
            from app.api.v1.endpoints.cobros.routes import (
                _invalidate_cobros_listado_kpis_cache,
            )

            if (
                res.marcado_importado_colision
                or res.importado_auto
                or res.a_en_revision
                or fant_rev
            ):
                _invalidate_cobros_listado_kpis_cache()
        except Exception:
            pass
    except Exception as e:
        logger.exception("[cobros] saneamiento limbo aprobado: %s", e)
    finally:
        db.close()


def _job_cobros_sanear_aprobado_limbo_barrido_fuerte() -> None:
    _job_cobros_sanear_aprobado_limbo(barrido_fuerte=True)


def _make_job_recibos_conciliacion(max_cedulas: Optional[int], slot_label: str) -> Callable[[], None]:
    def _run() -> None:
        db = SessionLocal()
        try:
            from app.services.cuota_estado import hoy_negocio
            from app.services.recibos_conciliacion_email_job import (
                ejecutar_recibos_envio_slot,
            )

            res = ejecutar_recibos_envio_slot(
                db,
                fecha_dia=hoy_negocio(),
                solo_simular=False,
                max_cedulas=max_cedulas,
            )
            logger.info(
                "[scheduler] recibos %s ejecutado fecha_dia=%s enviados=%s cedulas=%s max=%s",
                slot_label,
                res.get("fecha_dia"),
                res.get("enviados"),
                res.get("cedulas_distintas"),
                max_cedulas,
            )
        except Exception as e:
            logger.exception("[scheduler] recibos %s: %s", slot_label, e)
        finally:
            db.close()

    return _run


def _job_recibos_conciliacion_email_diario() -> None:
    """Compat: delega al primer slot con tope de lote."""
    _make_job_recibos_conciliacion(_recibos_batch_max(), "legacy")()


def _job_notificaciones_estado_cuenta_cron() -> None:
    """09:00 Caracas (+ catch-up horario): masivo ESTADO_CUENTA PDF (tope 600/día)."""
    db = SessionLocal()
    try:
        from app.services.estado_cuenta_notificacion_envio import (
            ejecutar_estado_cuenta_cron,
        )

        res = ejecutar_estado_cuenta_cron(db, origen="cron")
        logger.info(
            "[scheduler] ESTADO_CUENTA cron omitido=%s enviados=%s motivo=%s",
            res.get("omitido"),
            res.get("enviados"),
            res.get("motivo") or res.get("motivo_pausa"),
        )
    except Exception as e:
        logger.exception("[scheduler] ESTADO_CUENTA cron: %s", e)
    finally:
        db.close()


def start_scheduler() -> None:
    """Registra jobs en orden de flujo nocturno; horas espaciadas por carga (ver comentarios SCHEDULER_TZ).

    Un solo hilo de ejecución (ThreadPoolExecutor(1)) evita que dos jobs distintos se solapen en BD/API.
    """
    global _scheduler
    if _scheduler is not None:
        logger.warning("Scheduler ya estÃ¡ iniciado.")
        return
    _scheduler = BackgroundScheduler(
        timezone=SCHEDULER_TZ,
        executors={"default": ThreadPoolExecutor(1)},
        job_defaults={
            "max_instances": 1,
            "coalesce": True,
            "misfire_grace_time": 3600,
        },
    )
    _dow_all_week = "sun,mon,tue,wed,thu,fri,sat"

    # --- Registro en orden cronológico típico (Caracas) ---

    # Cobros: reconciliar reportados ya en cartera (45 min 08-20; cada 2h fuera).
    _scheduler.add_job(
        _wrap_job_with_timing(
            "cobros_reconciliar_reportados_cartera",
            _job_cobros_reconciliar_reportados_cartera,
        ),
        _cron_slots_or_trigger(
            COBROS_RECONCILIAR_DAY_SLOTS + COBROS_RECONCILIAR_OFFHOURS_SLOTS
        ),
        id="cobros_reconciliar_reportados_cartera",
        name="Cobros: marcar importado si pago ya en cartera (45m día / 2h noche)",
    )

    # Cobros: drenar aprobado en limbo (cada 30 min 08-20 Caracas).
    _scheduler.add_job(
        _wrap_job_with_timing(
            "cobros_sanear_aprobado_limbo",
            _job_cobros_sanear_aprobado_limbo,
        ),
        CronTrigger(
            hour="8-20",
            minute="0,30",
            timezone=SCHEDULER_TZ,
        ),
        id="cobros_sanear_aprobado_limbo",
        name="Cobros: sanear aprobado limbo (cada 30 min 08-20, lote 120)",
    )

    # Cobros: barrido fuerte limbo madrugada 03:30.
    _scheduler.add_job(
        _wrap_job_with_timing(
            "cobros_sanear_aprobado_limbo_barrido_0330",
            _job_cobros_sanear_aprobado_limbo_barrido_fuerte,
        ),
        CronTrigger(hour=3, minute=30, timezone=SCHEDULER_TZ),
        id="cobros_sanear_aprobado_limbo_barrido_0330",
        name="Cobros: barrido fuerte limbo 03:30 (lote 400)",
    )

    # 01:00 todos los días — Clientes (Drive): sync A:S + caché
    if getattr(settings, "ENABLE_DRIVE_CLIENTES_NIGHTLY_0100", True):
        _scheduler.add_job(
            _wrap_job_with_timing("drive_clientes_noche_0100", _job_drive_clientes_noche_0100),
            CronTrigger(
                day_of_week=_dow_all_week,
                hour=1,
                minute=0,
                timezone=SCHEDULER_TZ,
            ),
            id="drive_clientes_noche_0100",
            name="Clientes Drive: caché candidatos 01:00 (todos los días)",
        )

    # 02:00 todos los días — Préstamos candidatos Drive: sync A:S + snapshot
    if getattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY", True):
        _scheduler.add_job(
            _wrap_job_with_timing(
                "prestamo_candidatos_noche_0200", _job_prestamo_candidatos_noche_0200
            ),
            CronTrigger(
                day_of_week=_dow_all_week,
                hour=2,
                minute=0,
                timezone=SCHEDULER_TZ,
            ),
            id="prestamo_candidatos_noche_0200",
            name="Prestamos Drive: snapshot 02:00 (todos los días)",
        )

    # 03:00 todo — auditoría cartera (muy pesado)
    _scheduler.add_job(
        _wrap_job_with_timing("auditoria_cartera_prestamos_0300", _job_auditoria_cartera_prestamos),
        CronTrigger(hour=3, minute=0, timezone=SCHEDULER_TZ),
        id="auditoria_cartera_prestamos_0300",
        name="Auditoria cartera prestamos 03:00",
    )

    # 04:00 todo — limpieza códigos (ligero)
    _scheduler.add_job(
        _wrap_job_with_timing("limpiar_estado_cuenta_codigos", _job_limpiar_estado_cuenta_codigos),
        CronTrigger(hour=4, minute=0, timezone=SCHEDULER_TZ),
        id="limpiar_estado_cuenta_codigos",
        name="Limpiar cÃ³digos estado de cuenta 4:00",
    )

    # 04:05 todos los días — caché clientes Drive (medio; tras auditoría y limpieza)
    _scheduler.add_job(
        _wrap_job_with_timing("drive_clientes_candidatos_cache_0405", _job_drive_clientes_candidatos_cache),
        CronTrigger(
            day_of_week=_dow_all_week,
            hour=4,
            minute=5,
            timezone=SCHEDULER_TZ,
        ),
        id="drive_clientes_candidatos_cache_0405",
        name="Clientes Drive: caché candidatos 04:05 (todos los días)",
    )

    # 04:45 todos los días — snapshot préstamos solo recalculo (sync principal 02:00)
    if getattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY", True):
        _scheduler.add_job(
            _wrap_job_with_timing("prestamo_candidatos_drive_0445", _job_prestamo_candidatos_drive_refresh),
            CronTrigger(
                day_of_week=_dow_all_week,
                hour=4,
                minute=45,
                timezone=SCHEDULER_TZ,
            ),
            id="prestamo_candidatos_drive_0445",
            name="Prestamos: recalculo snapshot Drive 04:45 (sin sync Sheets)",
        )

    _gmail_log = ""
    if getattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", False):
        _gmail_hours = _pagos_gmail_scan_times_label()
        _scheduler.add_job(
            _wrap_job_with_timing(PAGOS_GMAIL_PENDING_SCAN_JOB_ID, _job_pagos_gmail_pending_scan),
            _pagos_gmail_scan_or_trigger(),
            id=PAGOS_GMAIL_PENDING_SCAN_JOB_ID,
            name=f"Gmail Pagos sin etiqueta Caracas ({_gmail_hours})",
        )
        _gmail_log = f"; Gmail pagos sin etiqueta Caracas {_gmail_hours}"
    _ae_log = ""
    if getattr(settings, "AUDITORIA_EMAIL_AUTO_ADVANCE_ENABLED", False):
        _ae_mins = int(
            getattr(settings, "AUDITORIA_EMAIL_AUTO_ADVANCE_INTERVAL_MINUTES", 5) or 5
        )
        _scheduler.add_job(
            _wrap_job_with_timing(
                AUDITORIA_EMAIL_AUTO_ADVANCE_JOB_ID, _job_auditoria_email_auto_advance
            ),
            IntervalTrigger(minutes=_ae_mins, timezone=SCHEDULER_TZ),
            id=AUDITORIA_EMAIL_AUTO_ADVANCE_JOB_ID,
            name=f"Auditoría Email auto-avance cada {_ae_mins} min",
        )
        _ae_log = f"; Auditoría Email auto-avance cada {_ae_mins} min"
    _bcv_log = ""
    if getattr(settings, "ENABLE_BCV_WIDGET_TASA_JOB", False):
        _bcv_hours = _bcv_widget_tasa_times_label()
        _scheduler.add_job(
            _wrap_job_with_timing(BCV_WIDGET_TASA_JOB_ID, _job_bcv_widget_tasa),
            _bcv_widget_tasa_or_trigger(),
            id=BCV_WIDGET_TASA_JOB_ID,
            name=f"BCV recuadro USD lun-vie Caracas ({_bcv_hours})",
        )
        _bcv_log = f"; BCV recuadro USD lun-vie Caracas {_bcv_hours}"
    # PAGO_2_DIAS_ANTES_PENDIENTE: slots madrugada + tarde si ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES.
    _cron_2d_log = "; notificaciones 2d antes: deshabilitado"
    if getattr(settings, "ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES", True):
        from app.services.notificaciones_cron_2_dias_antes_job import (
            horarios_cron_2_dias_antes,
        )

        _d2_slots = horarios_cron_2_dias_antes()
        _d2_label = ", ".join(f"{h:02d}:{m:02d}" for h, m in _d2_slots) or "00:48, 18:15"
        for h, m in _d2_slots:
            _jid = f"{CRON_2_DIAS_JOB_PREFIX}_{h:02d}{m:02d}"
            _scheduler.add_job(
                _wrap_job_with_timing(
                    _jid,
                    _job_notificaciones_pago_2_dias_antes_cron,
                ),
                CronTrigger(
                    hour=h,
                    minute=m,
                    timezone=SCHEDULER_TZ,
                ),
                id=_jid,
                name=(
                    f"Notificaciones 3 días antes (d-2-antes) "
                    f"{h:02d}:{m:02d} Caracas (lun-dom)"
                ),
            )
        _cron_2d_log = f"; notificaciones 2d antes {_d2_label} Caracas lun-dom"
    # PREJUDICIAL / a-2-cuotas: 02:22 Caracas lun–dom si ENABLE_CRON_NOTIFICACIONES_PREJUDICIAL.
    _cron_prej_log = "; notificaciones a-2-cuotas: deshabilitado"
    if getattr(settings, "ENABLE_CRON_NOTIFICACIONES_PREJUDICIAL", True):
        _hp = int(getattr(settings, "CRON_PREJUDICIAL_HOUR", 0) or 0)
        _mp = int(getattr(settings, "CRON_PREJUDICIAL_MINUTE", 20) or 20)
        _hp = max(0, min(23, _hp))
        _mp = max(0, min(59, _mp))
        _scheduler.add_job(
            _wrap_job_with_timing(
                PREJUDICIAL_2_CUOTAS_EMAIL_JOB_ID,
                _job_notificaciones_prejudicial_2_cuotas_cron,
            ),
            CronTrigger(
                hour=_hp,
                minute=_mp,
                timezone=SCHEDULER_TZ,
            ),
            id=PREJUDICIAL_2_CUOTAS_EMAIL_JOB_ID,
            name=(
                f"Notificaciones PREJUDICIAL a-2-cuotas "
                f"{_hp:02d}:{_mp:02d} Caracas (lun-dom)"
            ),
        )
        _cron_prej_log = (
            f"; notificaciones a-2-cuotas {_hp:02d}:{_mp:02d} Caracas lun-dom"
        )
    # atraso-10-dias: 02:40 Caracas lun–dom si ENABLE_CRON_NOTIFICACIONES_ATRASO_10_DIAS.
    _cron_a10_log = "; notificaciones atraso-10-dias: deshabilitado"
    if getattr(settings, "ENABLE_CRON_NOTIFICACIONES_ATRASO_10_DIAS", True):
        _ha = int(getattr(settings, "CRON_ATRASO_10_DIAS_HOUR", 13) or 13)
        _ma = int(getattr(settings, "CRON_ATRASO_10_DIAS_MINUTE", 15) or 15)
        _ha = max(0, min(23, _ha))
        _ma = max(0, min(59, _ma))
        _scheduler.add_job(
            _wrap_job_with_timing(
                ATRASO_10_DIAS_EMAIL_JOB_ID,
                _job_notificaciones_atraso_10_dias_cron,
            ),
            CronTrigger(
                hour=_ha,
                minute=_ma,
                timezone=SCHEDULER_TZ,
            ),
            id=ATRASO_10_DIAS_EMAIL_JOB_ID,
            name=(
                f"Notificaciones atraso-10-dias "
                f"{_ha:02d}:{_ma:02d} Caracas (lun-dom)"
            ),
        )
        _cron_a10_log = (
            f"; notificaciones atraso-10-dias {_ha:02d}:{_ma:02d} Caracas lun-dom"
        )
    # Día siguiente (/notificaciones): madrugada + tarde Caracas lun–dom.
    _cron_d1_log = "; notificaciones día siguiente: deshabilitado"
    if getattr(settings, "ENABLE_CRON_NOTIFICACIONES_DIA_SIGUIENTE", True):
        from app.services.notificaciones_cron_dia_siguiente_job import (
            horarios_cron_dia_siguiente,
        )

        _d1_slots = horarios_cron_dia_siguiente()
        _d1_label = ", ".join(f"{h:02d}:{m:02d}" for h, m in _d1_slots) or "02:08, 17:15"
        for h, m in _d1_slots:
            _jid = f"{CRON_DIA_SIGUIENTE_JOB_PREFIX}_{h:02d}{m:02d}"
            _scheduler.add_job(
                _wrap_job_with_timing(
                    _jid,
                    _job_notificaciones_dia_siguiente_cron,
                ),
                CronTrigger(
                    hour=h,
                    minute=m,
                    timezone=SCHEDULER_TZ,
                ),
                id=_jid,
                name=(
                    f"Notificaciones día siguiente (PAGO_1_DIA_ATRASADO) "
                    f"{h:02d}:{m:02d} Caracas (lun-dom)"
                ),
            )
        _cron_d1_log = (
            f"; notificaciones día siguiente {_d1_label} Caracas lun-dom"
        )
    # ESTADO_CUENTA: slots madrugada si ENABLE_CRON_NOTIFICACIONES_ESTADO_CUENTA.
    _estado_cuenta_cron_log = "; ESTADO_CUENTA: solo manual (cron deshabilitado)"
    if getattr(settings, "ENABLE_CRON_NOTIFICACIONES_ESTADO_CUENTA", True):
        _ec_slots = _estado_cuenta_cron_times()
        _ec_label = _cron_slots_label(_ec_slots)
        for h, m in _ec_slots:
            _jid = f"{ESTADO_CUENTA_CRON_JOB_PREFIX}_{h:02d}{m:02d}"
            _scheduler.add_job(
                _wrap_job_with_timing(
                    _jid,
                    _job_notificaciones_estado_cuenta_cron,
                ),
                CronTrigger(
                    hour=h,
                    minute=m,
                    timezone=SCHEDULER_TZ,
                ),
                id=_jid,
                name=(
                    f"Notificaciones ESTADO_CUENTA "
                    f"{h:02d}:{m:02d} Caracas (lun-dom)"
                ),
            )
        _estado_cuenta_cron_log = f"; ESTADO_CUENTA {_ec_label} Caracas lun-dom"
    # Recibos: horarios fijos lun-dom si ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS.
    _recibos_cron_log = "; recibos: solo manual (cron deshabilitado)"
    if getattr(settings, "ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS", False):
        _rec_slots = _recibos_cron_times()
        _batch_max = _recibos_batch_max()
        for h, m in _rec_slots:
            _slot_lbl = f"{h:02d}:{m:02d}"
            _jid = f"{RECIBOS_CRON_JOB_PREFIX}_{h:02d}{m:02d}"
            _max_ced = None if (h, m) == (21, 0) else _batch_max
            _scheduler.add_job(
                _wrap_job_with_timing(
                    _jid,
                    _make_job_recibos_conciliacion(_max_ced, _slot_lbl),
                ),
                CronTrigger(
                    day_of_week=_dow_all_week,
                    hour=h,
                    minute=m,
                    timezone=SCHEDULER_TZ,
                ),
                id=_jid,
                name=(
                    f"Recibos estado de cuenta {_slot_lbl} Caracas "
                    f"({'sin tope' if _max_ced is None else f'max {_max_ced} cédulas'})"
                ),
            )
        _recibos_cron_log = f"; recibos {_recibos_cron_times_label()}"
    _gestores_cron_log = "; gestores cobranza email: deshabilitado"
    if getattr(settings, "ENABLE_COBRANZA_GESTORES_EMAIL_JOB", True):
        _scheduler.add_job(
            _wrap_job_with_timing(
                "cobranza_gestores_email_1800",
                _job_cobranza_gestores_email_1800,
            ),
            CronTrigger(hour=18, minute=0, timezone=SCHEDULER_TZ),
            id="cobranza_gestores_email_1800",
            name="Gestores cobranza: Excel 18:00 Caracas a operaciones@",
        )
        _gestores_cron_log = "; gestores cobranza Excel 18:00 Caracas"
    # Cobranza por segmento: manual salvo cron «2 días antes» si ENABLE_*.
    # Recibos: disparo inmediato al alta en cartera + cron de cierre si ENABLE_*.
    # ESTADO_CUENTA: cron opcional 09:00 Caracas si ENABLE_CRON_NOTIFICACIONES_ESTADO_CUENTA.
    _scheduler.start()
    _drive_night_log = ""
    if getattr(settings, "ENABLE_DRIVE_CLIENTES_NIGHTLY_0100", True):
        _drive_night_log += "; Clientes Drive 01:00 (sync A:S + caché)"
    _prest_cand_log = ""
    if getattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY", True):
        _prest_cand_log = "; Prestamos Drive 02:00 (sync A:S + snapshot); recalculo 04:45"
    logger.info(
        "Scheduler iniciado%s; auditoria 03:00%s; "
        "caché Clientes Drive respaldo 04:05; limpieza estado_cuenta_codigos 4:00%s (%s).",
        _drive_night_log,
        _prest_cand_log,
        _gmail_log
        + _ae_log
        + _bcv_log
        + _cron_2d_log
        + _cron_prej_log
        + _cron_a10_log
        + _cron_d1_log
        + _estado_cuenta_cron_log
        + _recibos_cron_log
        + _gestores_cron_log,
        SCHEDULER_TZ,
    )
    if getattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", False):
        _gj = _scheduler.get_job(PAGOS_GMAIL_PENDING_SCAN_JOB_ID)
        if _gj is not None:
            logger.info(
                "[PAGOS_GMAIL] Job %s proxima_ejecucion=%s (referencia tz=%s)",
                _gj.id,
                _gj.next_run_time,
                SCHEDULER_TZ,
            )
    try:
        from app.services.cobranzas.gestores_email_diario_job import (
            catch_up_gestores_email_si_pendiente,
        )

        catch_up_gestores_email_si_pendiente()
    except Exception as e:
        logger.warning("[gestores] catch-up email al iniciar scheduler: %s", e)
    try:
        from app.services.estado_cuenta_notificacion_envio import (
            catch_up_estado_cuenta_si_pendiente,
        )

        catch_up_estado_cuenta_si_pendiente()
    except Exception as e:
        logger.warning("[ESTADO_CUENTA] catch-up al iniciar scheduler: %s", e)


def stop_scheduler() -> None:
    """Detiene el scheduler (Ãºtil en tests o shutdown)."""
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("Scheduler detenido.")
