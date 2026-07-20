"""
Scheduler para tareas programadas (zona America/Caracas).

Solo se registra e inicia si en el arranque ENABLE_AUTOMATIC_SCHEDULED_JOBS=true en settings (.env).
Por defecto esta desactivado: ningun cron en servidor; la pantalla Configuracion no dispara estos jobs.

Cuando esta activo:
- finiquito: refresco automatico periodico cada N minutos (configurable) y ventanas de respaldo 00:45 + 13:00 lun-sab.
- todos los dias 01:00  Clientes (Drive): sync A:S, import automático filas seleccionable; resto en pantalla (ENABLE_DRIVE_CLIENTES_NIGHTLY_0100 / AUTO_GUARDAR).
- todos los dias 02:00  Préstamos Drive: sync A:S, snapshot, guardar automático al 100% (_motivos_no_100); resto en pantalla (ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY / AUTO_GUARDAR).
- 03:00  Auditoria cartera: evaluacion de prestamos y metadatos en configuracion.
- 04:00  Limpieza codigos estado de cuenta.
- todos los dias 04:05  Caché lista «Clientes (Drive)» solo recalculo (sin sync Sheets; respaldo tras auditoría).
- todos los dias 04:45  Snapshot candidatos préstamo solo recalculo (sin sync; respaldo).
- domingo 04:35  Notificaciones: caché «Diferencia abono» (masivo préstamos), si ENABLE_ABONOS_DRIVE_CACHE_NIGHTLY (separado de limpieza 04:00 y del job fecha).
- lunes y jueves 04:00  Notificaciones: caché columna Q vs fecha_aprobacion (masivo), si ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY
  (misma hora que limpieza códigos: un hilo; orden de registro en scheduler; además se recalcula tras cada sync Drive exitoso).
- todos los dias cada hora a :30 entre 06:30 y 19:30  Gmail pendientes (si PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED=true).
- Recibos (correo estado de cuenta tras pagos conciliados): manual (POST /notificaciones/recibos/ejecutar) y,
  si ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS, cron diario RECIBOS_CRON_HOUR:RECIBOS_CRON_MINUTE Caracas
  (por defecto 11:50).
- Opcional: envío automático solo «2 días antes» (PAGO_2_DIAS_ANTES_PENDIENTE) si ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES
  (hora CRON_2_DIAS_ANTES_HOUR:CRON_2_DIAS_ANTES_MINUTE Caracas; idempotencia en configuracion).

Reportes cobranzas, informe de pagos por email y campanas CRM: manual o bajo demanda.

Criterios al cambiar horarios (carga, colisiones, dependencias): comentarios en este módulo y Field descriptions en Settings.
"""
import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

# Zona horaria por defecto (Venezuela). Configurable vÃ­a env si se aÃ±ade SCHEDULER_TZ.
SCHEDULER_TZ = "America/Caracas"

# Complejidad aproximada (duración / carga BD) — guía al espaciar triggers y evitar el mismo minuto:
#   Muy pesado: sync CONCILIACIÓN (Sheets + bulk), auditoría cartera, caché abonos masivo, caché fecha Q masivo.
#   Medio: snapshot prestamo_candidatos_drive, caché clientes Drive.
#   Ligero: limpieza estado_cuenta_codigos.
# Dependencia: sync dom/mié 01:20 alimenta `drive` y dispara recálculo masivo Q vs BD en la respuesta del sync; jobs que leen `drive` (clientes 04:05, candidatos 04:45, todos los días)
# corren tras auditoría 03:00 y limpieza 04:00 para no competir con la carga de la BD en el mismo tramo que el sync.
# El pool del scheduler usa 1 hilo: ningún job se solapa con otro (evita colisiones DB/API).

# Debe coincidir con el id en add_job (Gmail pendientes diario :30).
PAGOS_GMAIL_PENDING_SCAN_JOB_ID = "pagos_gmail_pending_scan_daily_0630_1930"

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


def _job_abonos_drive_cuotas_cache_dom_0435() -> None:
    """Domingo 04:35 Caracas (tras sync dom/mié 01:20; separado de limpieza 04:00 y del job fecha Q). Persiste ABONOS vs cuotas en prestamos."""
    if not getattr(settings, "ENABLE_ABONOS_DRIVE_CACHE_NIGHTLY", True):
        return
    db = SessionLocal()
    try:
        from app.services.abonos_drive_cuotas_cache_job import (
            ejecutar_refresh_abonos_drive_cuotas_cache_nightly,
        )

        res = ejecutar_refresh_abonos_drive_cuotas_cache_nightly(db)
        logger.info(
            "[abonos_drive_cache] nightly prestamos=%s ok=%s err=%s skip=%s",
            res.get("prestamos_considerados"),
            res.get("actualizados_ok"),
            res.get("errores"),
            res.get("omitidos_sin_cedula"),
        )
    except Exception as e:
        logger.exception("Error en job abonos_drive_cuotas_cache_dom_0435: %s", e)
    finally:
        db.close()


def _job_abonos_drive_autosync_dom_0510() -> None:
    """Domingo 05:10 Caracas: aplica automáticamente diferencias ABONOS->cuotas (modo real, seguro)."""
    if not getattr(settings, "ENABLE_ABONOS_DRIVE_AUTOSYNC_NIGHTLY", False):
        return
    db = SessionLocal()
    try:
        from app.services.sincronizar_abonos_drive_cuotas_service import (
            sincronizar_abonos_drive_a_cuotas_masivo,
        )

        res = sincronizar_abonos_drive_a_cuotas_masivo(
            db,
            dry_run=False,
            limit=0,
            prestamo_id=None,
            aplicar_montos_altos=False,
            usuario_registro="AUTO_CRON_ABONOS_DRIVE",
        )
        logger.info(
            "[abonos_drive_autosync] programado total=%s aplicables=%s aplicados=%s omitidos_lote=%s omitidos_monto_alto=%s errores=%s",
            (res.get("resumen") or {}).get("total_evaluados"),
            (res.get("resumen") or {}).get("con_diferencia_aplicable"),
            (res.get("resumen") or {}).get("aplicados"),
            (res.get("resumen") or {}).get("omitidos_requiere_lote"),
            (res.get("resumen") or {}).get("omitidos_monto_alto"),
            (res.get("resumen") or {}).get("errores"),
        )
    except Exception as e:
        logger.exception("Error en job abonos_drive_autosync_dom_0510: %s", e)
    finally:
        db.close()


def _job_fecha_entrega_q_aprobacion_cache_lun_jue_0400() -> None:
    """Lunes y jueves 04:00 Caracas. Columna Q vs fecha_aprobacion en prestamos (Notificaciones Fecha)."""
    if not getattr(settings, "ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY", True):
        return
    db = SessionLocal()
    try:
        from app.services.fecha_entrega_q_aprobacion_cache_job import (
            ejecutar_refresh_fecha_entrega_q_aprobacion_cache_nightly,
        )

        res = ejecutar_refresh_fecha_entrega_q_aprobacion_cache_nightly(db)
        logger.info(
            "[fecha_q_cache] programado lun/jue prestamos=%s ok=%s err=%s skip=%s",
            res.get("prestamos_considerados"),
            res.get("actualizados_ok"),
            res.get("errores"),
            res.get("omitidos_sin_cedula"),
        )
    except Exception as e:
        logger.exception("Error en job fecha_entrega_q_aprobacion_cache_lun_jue_0400: %s", e)
    finally:
        db.close()


def _job_finiquito_refresh() -> None:
    """Lunes a sabado 01:00 y 13:00 Caracas. Rellena/actualiza finiquito_casos (solo LIQUIDADO con suma cuotas = total_financiamiento)."""
    db = SessionLocal()
    try:
        from app.services.finiquito_refresh import ejecutar_refresh_finiquito_casos

        res = ejecutar_refresh_finiquito_casos(db)
        logger.info(
            "Finiquito refresh: elegibles=%s insertados=%s actualizados=%s eliminados=%s",
            res.get("elegibles"),
            res.get("insertados"),
            res.get("actualizados"),
            res.get("eliminados"),
        )
    except Exception as e:
        logger.exception("Error en job finiquito_refresh: %s", e)
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


def _job_hoja_drive_conciliacion_sync() -> None:
    """Sync CONCILIACIÓN (rango A:S hasta última fila con dato en cualquier columna). Usado por jobs 01:00 y 02:00."""
    db = SessionLocal()
    try:
        from app.services.conciliacion_sheet_sync import run_sync_to_db

        res = run_sync_to_db(db)
        logger.info(
            "[drive/conciliacion_sheet] Sync OK filas=%s ultima_fila_a=%s run_id=%s",
            res.get("row_count"),
            res.get("column_a_last_row"),
            res.get("run_id"),
        )
        return res
    except ValueError as e:
        logger.warning(
            "[drive/conciliacion_sheet] Sync omitido o no configurado: %s",
            e,
        )
        return None
    except Exception as e:
        logger.exception("[drive/conciliacion_sheet] Sync error: %s", e)
        raise
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
        from app.services.fecha_entrega_q_aprobacion_cache_job import (
            ejecutar_refresh_fecha_entrega_q_cache_tras_sync_conciliacion,
        )

        res = run_sync_to_db(db)
        try:
            ejecutar_refresh_fecha_entrega_q_cache_tras_sync_conciliacion(db)
        except Exception as qe:
            logger.warning("[drive_clientes_0100] refresco Q tras sync: %s", qe)
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
    """04:45 Caracas: solo recalcula prestamo_candidatos_drive desde `drive` (sin sync Sheets)."""
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
    """04:05 Caracas: solo recalcula drive_clientes_candidatos_cache (sync principal a las 01:00)."""
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
    """Todos los dias cada hora :30 entre 06:30 y 19:30 (America/Caracas): pipeline Gmail."""
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
            "[PAGOS_GMAIL] Escaneo programado: all (leídos + no leídos) sync_id=%s",
            sync.id,
        )
        schedule_gmail_pipeline_background(sync.id, scan_filter="all")
    except Exception as e:
        logger.exception("[PAGOS_GMAIL] Escaneo programado: %s", e)
    finally:
        db.close()


def _job_notificaciones_pago_2_dias_antes_cron() -> None:
    """Diario (Caracas): envío automático solo «2 días antes» si ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES."""
    if not getattr(settings, "ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES", False):
        return
    from app.services.notificaciones_cron_2_dias_antes_job import job_cron_pago_2_dias_antes_scheduler

    job_cron_pago_2_dias_antes_scheduler()


def _job_recibos_conciliacion_email_diario() -> None:
    """Diario Caracas: envío Recibos (misma lógica que POST /notificaciones/recibos/ejecutar para hoy)."""
    if not getattr(settings, "ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS", False):
        return
    from app.core.database import SessionLocal
    from app.services.recibos_conciliacion_email_job import job_recibos_programado_caracas

    db = SessionLocal()
    try:
        job_recibos_programado_caracas(db)
    except Exception as e:
        logger.exception("[recibos] cron diario: %s", e)
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
    _dow_lun_sab = "mon,tue,wed,thu,fri,sat"
    _dow_all_week = "sun,mon,tue,wed,thu,fri,sat"

    # --- Registro en orden cronológico típico (Caracas) ---

    # Finiquito cada N minutos (operativo): mantiene la bandeja fresca sin esperar horarios fijos.
    if getattr(settings, "ENABLE_FINIQUITO_REFRESH_INTERVAL", True):
        _minutes = int(getattr(settings, "FINIQUITO_REFRESH_INTERVAL_MINUTES", 15) or 15)
        _minutes = max(5, min(_minutes, 180))
        _scheduler.add_job(
            _wrap_job_with_timing("finiquito_refresh_interval", _job_finiquito_refresh),
            IntervalTrigger(
                minutes=_minutes,
                timezone=SCHEDULER_TZ,
            ),
            id="finiquito_refresh_interval",
            name=f"Finiquito: refresco periodico cada {_minutes} min",
        )

    # 00:45 lun-sab — finiquito (respaldo nocturno; antes del sync Drive 01:00)
    _scheduler.add_job(
        _wrap_job_with_timing("finiquito_refresh_lun_sab_0045", _job_finiquito_refresh),
        CronTrigger(
            day_of_week=_dow_lun_sab,
            hour=0,
            minute=45,
            timezone=SCHEDULER_TZ,
        ),
        id="finiquito_refresh_lun_sab_0045",
        name="Finiquito: refrescar casos lun-sab 00:45",
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
            name="Clientes Drive: sync A:S + caché 01:00 (todos los días)",
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
            name="Prestamos Drive: sync A:S + snapshot 02:00 (todos los días)",
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

    # 04:35 domingo — caché abonos masivo (Notificaciones General)
    if getattr(settings, "ENABLE_ABONOS_DRIVE_CACHE_NIGHTLY", True):
        _scheduler.add_job(
            _wrap_job_with_timing("abonos_drive_cuotas_cache_dom_0435", _job_abonos_drive_cuotas_cache_dom_0435),
            CronTrigger(day_of_week="sun", hour=4, minute=35, timezone=SCHEDULER_TZ),
            id="abonos_drive_cuotas_cache_dom_0435",
            name="Notificaciones: caché Diferencia abono (hoja vs cuotas) domingo 04:35",
        )
    if getattr(settings, "ENABLE_ABONOS_DRIVE_AUTOSYNC_NIGHTLY", False):
        _scheduler.add_job(
            _wrap_job_with_timing("abonos_drive_autosync_dom_0510", _job_abonos_drive_autosync_dom_0510),
            CronTrigger(day_of_week="sun", hour=5, minute=10, timezone=SCHEDULER_TZ),
            id="abonos_drive_autosync_dom_0510",
            name="Notificaciones: autosync ABONOS->cuotas domingo 05:10",
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

    # 04:00 lunes y jueves — caché columna Q vs aprobación (Notificaciones Fecha)
    if getattr(settings, "ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY", True):
        _scheduler.add_job(
            _wrap_job_with_timing(
                "fecha_entrega_q_aprobacion_cache_lun_0400",
                _job_fecha_entrega_q_aprobacion_cache_lun_jue_0400,
            ),
            CronTrigger(day_of_week="mon", hour=4, minute=0, timezone=SCHEDULER_TZ),
            id="fecha_entrega_q_aprobacion_cache_lun_0400",
            name="Notificaciones: caché Q vs fecha_aprobacion lunes 04:00",
        )
        _scheduler.add_job(
            _wrap_job_with_timing(
                "fecha_entrega_q_aprobacion_cache_jue_0400",
                _job_fecha_entrega_q_aprobacion_cache_lun_jue_0400,
            ),
            CronTrigger(day_of_week="thu", hour=4, minute=0, timezone=SCHEDULER_TZ),
            id="fecha_entrega_q_aprobacion_cache_jue_0400",
            name="Notificaciones: caché Q vs fecha_aprobacion jueves 04:00",
        )

    # 13:00 lun-sab — finiquito (respaldo mediodia)
    _scheduler.add_job(
        _wrap_job_with_timing("finiquito_refresh_lun_sab_1300", _job_finiquito_refresh),
        CronTrigger(
            day_of_week=_dow_lun_sab,
            hour=13,
            minute=0,
            timezone=SCHEDULER_TZ,
        ),
        id="finiquito_refresh_lun_sab_1300",
        name="Finiquito: refrescar casos lun-sab 13:00",
    )

    _gmail_log = ""
    if getattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", False):
        _scheduler.add_job(
            _wrap_job_with_timing(PAGOS_GMAIL_PENDING_SCAN_JOB_ID, _job_pagos_gmail_pending_scan),
            CronTrigger(
                hour="6-19",
                minute=30,
                timezone=SCHEDULER_TZ,
            ),
            id=PAGOS_GMAIL_PENDING_SCAN_JOB_ID,
            name="Gmail Pagos pendientes cada dia :30 (06:30-19:30 Caracas)",
        )
        _gmail_log = (
            "; Gmail pagos pendientes todos los dias cada hora :30 entre 06:30 y 19:30"
        )
    _cron_2d_log = ""
    if getattr(settings, "ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES", False):
        _h = int(getattr(settings, "CRON_2_DIAS_ANTES_HOUR", 7) or 7)
        _m = int(getattr(settings, "CRON_2_DIAS_ANTES_MINUTE", 0) or 0)
        _h = max(0, min(_h, 23))
        _m = max(0, min(_m, 59))
        _scheduler.add_job(
            _wrap_job_with_timing(
                "notificaciones_pago_2_dias_antes_diario",
                _job_notificaciones_pago_2_dias_antes_cron,
            ),
            CronTrigger(hour=_h, minute=_m, timezone=SCHEDULER_TZ),
            id="notificaciones_pago_2_dias_antes_diario",
            name=f"Notificaciones: PAGO_2_DIAS_ANTES diario {_h:02d}:{_m:02d} Caracas",
        )
        _cron_2d_log = f"; notificaciones 2 dias antes diario {_h:02d}:{_m:02d} Caracas"
    _recibos_cron_log = ""
    if getattr(settings, "ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS", False):
        _rh = int(getattr(settings, "RECIBOS_CRON_HOUR", 11) or 11)
        _rm = int(getattr(settings, "RECIBOS_CRON_MINUTE", 50) or 50)
        _rh = max(0, min(_rh, 23))
        _rm = max(0, min(_rm, 59))
        _scheduler.add_job(
            _wrap_job_with_timing(
                "recibos_conciliacion_email_diario",
                _job_recibos_conciliacion_email_diario,
            ),
            CronTrigger(hour=_rh, minute=_rm, timezone=SCHEDULER_TZ),
            id="recibos_conciliacion_email_diario",
            name=f"Recibos: envío conciliación diario {_rh:02d}:{_rm:02d} Caracas",
        )
        _recibos_cron_log = f"; recibos conciliacion diario {_rh:02d}:{_rm:02d} Caracas"
    # Otros envíos por pestaña (previas, mora, masivos): manual desde la UI (POST).
    # PREJUDICIAL (60+ días) y PAGO_10_DIAS_ATRASADO: solo manual (sin cron ni enviar-todas).
    _scheduler.start()
    _caches_notif_log = ""
    if getattr(settings, "ENABLE_ABONOS_DRIVE_CACHE_NIGHTLY", True):
        _caches_notif_log += "; caché Diferencia abono domingo 04:35"
    if getattr(settings, "ENABLE_ABONOS_DRIVE_AUTOSYNC_NIGHTLY", False):
        _caches_notif_log += "; autosync ABONOS->cuotas domingo 05:10"
    if getattr(settings, "ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY", True):
        _caches_notif_log += "; caché Q vs aprobación lunes y jueves 04:00"
    _drive_night_log = ""
    if getattr(settings, "ENABLE_DRIVE_CLIENTES_NIGHTLY_0100", True):
        _drive_night_log += "; Clientes Drive 01:00 (sync A:S + caché)"
    _prest_cand_log = ""
    if getattr(settings, "ENABLE_PRESTAMO_CANDIDATOS_DRIVE_NIGHTLY", True):
        _prest_cand_log = "; Prestamos Drive 02:00 (sync A:S + snapshot); recalculo 04:45"
    logger.info(
        "Scheduler iniciado: finiquito lun-sab 00:45 y 13:00%s; auditoria 03:00%s%s; "
        "caché Clientes Drive respaldo 04:05; limpieza estado_cuenta_codigos 4:00%s (%s).",
        _drive_night_log,
        _caches_notif_log,
        _prest_cand_log,
        _gmail_log + _cron_2d_log + _recibos_cron_log,
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


def stop_scheduler() -> None:
    """Detiene el scheduler (Ãºtil en tests o shutdown)."""
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("Scheduler detenido.")
