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
- todos los dias (America/Caracas) Gmail sin etiqueta de usuario a las
  08:00, 08:30, 09:30, 10:30, 12:00, 14:00, 14:30, 15:00, 15:30, 16:00, 16:30, 17:30, 20:00
  (si PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED=true).
- lun-vie America/Caracas: bot de un GET al recuadro USD de bcv.org.ve (si ENABLE_BCV_WIDGET_TASA_JOB=true)
  a las 08:30 (recupero), 16:00, 16:30, 17:00, 17:30, 18:00 y 18:30. El BCV publica la tasa del
  siguiente día hábil en la tarde (~16:00–18:30 Caracas; el viernes cubre el lunes). Si ya hay
  tasa_bcv para ese día hábil siguiente, el job no vuelve a pegarle a la portada.
- Recibos (correo estado de cuenta tras pagos conciliados): manual (POST /notificaciones/recibos/ejecutar) y,
  si ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS, cron lun-vie cada hora RECIBOS_CRON_HOUR_START–END:MINUTE Caracas
  (por defecto 08:00–20:00; sáb/dom no).
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
from apscheduler.triggers.combining import OrTrigger
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

# Horarios fijos America/Caracas (no cada 30 min). Debe coincidir con el id en add_job.
PAGOS_GMAIL_SCHEDULED_SCAN_TIMES: tuple[tuple[int, int], ...] = (
    (8, 0),
    (8, 30),
    (9, 30),
    (10, 30),
    (12, 0),
    (14, 0),
    (14, 30),
    (15, 0),
    (15, 30),
    (16, 0),
    (16, 30),
    (17, 30),
    (20, 0),
)
PAGOS_GMAIL_PENDING_SCAN_JOB_ID = "pagos_gmail_pending_scan_caracas"
BCV_WIDGET_TASA_JOB_ID = "bcv_widget_tasa_caracas"
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


def _pagos_gmail_scan_times_label() -> str:
    return ", ".join(f"{h:02d}:{m:02d}" for h, m in PAGOS_GMAIL_SCHEDULED_SCAN_TIMES)


def _pagos_gmail_scan_or_trigger() -> OrTrigger:
    return OrTrigger(
        [
            CronTrigger(hour=h, minute=m, timezone=SCHEDULER_TZ)
            for h, m in PAGOS_GMAIL_SCHEDULED_SCAN_TIMES
        ]
    )

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
    """Reservado: politicamente desactivado. Toda cobranza es solo manual."""
    logger.info(
        "[scheduler] cron 2 dias antes omitido: politica solo-manual "
        "(usar POST /notificaciones/enviar-caso-manual)"
    )
    return



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


def _job_cobros_sanear_aprobado_limbo() -> None:
    """Drena limbo aprobado + recupera en_revision current_user + Gmail traza + purge."""
    db = SessionLocal()
    try:
        from app.services.cobros.saneamiento_aprobado_limbo import (
            sanear_aprobados_en_limbo,
            sanear_en_revision_recuperables,
            sanear_importados_sin_cartera_aplicada,
        )

        # Oldest-first para drenar backlog histórico; lotes acotados por ciclo.
        res = sanear_aprobados_en_limbo(
            db,
            max_ids=120,
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


def _job_recibos_conciliacion_email_diario() -> None:
    """Catch-up horario lun-vie: envía Recibos a cédulas pendientes de hoy (misma lógica que POST ejecutar)."""
    db = SessionLocal()
    try:
        from app.services.cuota_estado import hoy_negocio
        from app.services.recibos_conciliacion_email_job import (
            job_recibos_programado_caracas,
        )

        job_recibos_programado_caracas(db)
        logger.info(
            "[scheduler] recibos horario ejecutado fecha_dia=%s",
            hoy_negocio().isoformat(),
        )
    except Exception as e:
        logger.exception("[scheduler] recibos horario: %s", e)
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


    # Cobros: reconciliar reportados ya en cartera (no dejar aprobado/en_revision huérfanos).
    _scheduler.add_job(
        _wrap_job_with_timing(
            "cobros_reconciliar_reportados_cartera",
            _job_cobros_reconciliar_reportados_cartera,
        ),
        IntervalTrigger(
            minutes=20,
            timezone=SCHEDULER_TZ,
        ),
        id="cobros_reconciliar_reportados_cartera",
        name="Cobros: marcar importado si pago ya en cartera (cada 20 min)",
    )

    # Cobros: drenar aprobado en limbo (cargar con datos reales o pasar a revisión).
    _scheduler.add_job(
        _wrap_job_with_timing(
            "cobros_sanear_aprobado_limbo",
            _job_cobros_sanear_aprobado_limbo,
        ),
        IntervalTrigger(
            minutes=15,
            timezone=SCHEDULER_TZ,
        ),
        id="cobros_sanear_aprobado_limbo",
        name="Cobros: sanear aprobado limbo (cada 15 min, lote 120)",
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
        _gmail_hours = _pagos_gmail_scan_times_label()
        _scheduler.add_job(
            _wrap_job_with_timing(PAGOS_GMAIL_PENDING_SCAN_JOB_ID, _job_pagos_gmail_pending_scan),
            _pagos_gmail_scan_or_trigger(),
            id=PAGOS_GMAIL_PENDING_SCAN_JOB_ID,
            name=f"Gmail Pagos sin etiqueta Caracas ({_gmail_hours})",
        )
        _gmail_log = f"; Gmail pagos sin etiqueta Caracas {_gmail_hours}"
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
    # Politica: sin cron de notificaciones de cobranza (solo POST manual).
    # ENABLE_CRON_NOTIFICACIONES_2_DIAS_ANTES se ignora a proposito.
    _cron_2d_log = "; notificaciones cobranza: solo manual (cron 2d deshabilitado)"
    # Recibos: catch-up lun-vie cada hora (pendientes del día) si ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS.
    _recibos_cron_log = "; recibos: solo manual (cron deshabilitado)"
    if getattr(settings, "ENABLE_RECIBOS_CONCILIACION_EMAIL_JOBS", False):
        _rh_start = int(getattr(settings, "RECIBOS_CRON_HOUR_START", 8) or 8)
        _rh_end = int(getattr(settings, "RECIBOS_CRON_HOUR_END", 20) or 20)
        _rm = int(getattr(settings, "RECIBOS_CRON_MINUTE", 0) or 0)
        _rh_start = max(0, min(_rh_start, 23))
        _rh_end = max(0, min(_rh_end, 23))
        if _rh_end < _rh_start:
            _rh_start, _rh_end = _rh_end, _rh_start
        _rm = max(0, min(_rm, 59))
        _scheduler.add_job(
            _wrap_job_with_timing(
                "recibos_conciliacion_email_diario",
                _job_recibos_conciliacion_email_diario,
            ),
            CronTrigger(
                day_of_week="mon-fri",
                hour=f"{_rh_start}-{_rh_end}",
                minute=_rm,
                timezone=SCHEDULER_TZ,
            ),
            id="recibos_conciliacion_email_diario",
            name=(
                f"Recibos estado de cuenta lun-vie "
                f"{_rh_start:02d}-{_rh_end:02d}:{_rm:02d} Caracas"
            ),
        )
        _recibos_cron_log = (
            f"; recibos lun-vie cada hora {_rh_start:02d}-{_rh_end:02d}:{_rm:02d} Caracas"
        )
    # Todos los envios de notificaciones de cobranza: solo manual desde la UI (POST).
    # Recibos: disparo inmediato al alta en cartera + cron de cierre si ENABLE_*.
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
        _gmail_log + _bcv_log + _cron_2d_log + _recibos_cron_log,
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
