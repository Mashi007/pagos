"""
Scheduler para tareas programadas (zona America/Caracas).

Solo se registra e inicia si en el arranque ENABLE_AUTOMATIC_SCHEDULED_JOBS=true en settings (.env).
Por defecto esta desactivado: ningun cron en servidor; la pantalla Configuracion no dispara estos jobs.

Cuando esta activo:
- 02:00  Finiquito: refrescar tabla finiquito_casos.
- domingo 02:00  Notificaciones: caché «Diferencia abono» (ABONOS hoja vs cuotas) en prestamos, si ENABLE_ABONOS_DRIVE_CACHE_NIGHTLY.
- domingo 02:03  Notificaciones: caché columna Q vs fecha_aprobacion en prestamos, si ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY.
- 03:00  Auditoria cartera: evaluacion de prestamos y metadatos en configuracion.
- 03:00  Notificaciones «2 dias antes» (PAGO_2_DIAS_ANTES_PENDIENTE): solo si cron_envio_pago_2_dias_antes.habilitado en BD; no afecta otros casos.
- 04:00  Limpieza codigos estado de cuenta.
- 04:01  Hoja CONCILIACION (Google Sheets) -> BD: conciliacion_sheet_* y tabla drive (columnas A..S).
- 04:00, 11:00, 20:00  Gmail (si PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED=true).

Reportes cobranzas, informe de pagos por email y campanas CRM: manual o bajo demanda.
"""
import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

# Zona horaria por defecto (Venezuela). Configurable vÃ­a env si se aÃ±ade SCHEDULER_TZ.
SCHEDULER_TZ = "America/Caracas"

_scheduler: Optional[BackgroundScheduler] = None


def scheduler_is_running() -> bool:
    """True si este proceso ya tiene BackgroundScheduler iniciado (lider con jobs registrados)."""
    return _scheduler is not None


def _job_abonos_drive_cuotas_cache_0200() -> None:
    """Domingo 02:00 Caracas. Persiste comparación ABONOS (hoja) vs cuotas en prestamos (columna Notificaciones General)."""
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
        logger.exception("Error en job abonos_drive_cuotas_cache_0200: %s", e)
    finally:
        db.close()


def _job_fecha_entrega_q_aprobacion_cache_0203() -> None:
    """Domingo 02:03 Caracas. Columna Q (hoja) vs fecha_aprobacion en prestamos (Notificaciones Fecha)."""
    if not getattr(settings, "ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY", True):
        return
    db = SessionLocal()
    try:
        from app.services.fecha_entrega_q_aprobacion_cache_job import (
            ejecutar_refresh_fecha_entrega_q_aprobacion_cache_nightly,
        )

        res = ejecutar_refresh_fecha_entrega_q_aprobacion_cache_nightly(db)
        logger.info(
            "[fecha_q_cache] nightly prestamos=%s ok=%s err=%s skip=%s",
            res.get("prestamos_considerados"),
            res.get("actualizados_ok"),
            res.get("errores"),
            res.get("omitidos_sin_cedula"),
        )
    except Exception as e:
        logger.exception("Error en job fecha_entrega_q_aprobacion_cache_0203: %s", e)
    finally:
        db.close()


def _job_finiquito_refresh() -> None:
    """Job 02:00. Rellena/actualiza finiquito_casos (solo LIQUIDADO con suma cuotas = total_financiamiento)."""
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


def _job_notificaciones_pago_2_dias_antes_0300() -> None:
    """
    03:00 Caracas. Únicamente el caso PAGO_2_DIAS_ANTES_PENDIENTE si está habilitado en
    configuracion.notificaciones_envios → cron_envio_pago_2_dias_antes.habilitado.
    No dispara previas, retrasadas, prejudicial ni masivos.
    """
    try:
        from app.services.notificaciones_cron_pago_2_dias_antes import (
            job_wrapper_cron_pago_2_dias_antes,
        )

        job_wrapper_cron_pago_2_dias_antes()
    except Exception as e:
        logger.exception("Error en job notificaciones_pago_2_dias_antes_0300: %s", e)


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
    """04:01 (America/Caracas): descarga pestaña CONCILIACIÓN A:S y rellena conciliacion_sheet_* + drive."""
    db = SessionLocal()
    try:
        from app.services.conciliacion_sheet_sync import run_sync_to_db

        res = run_sync_to_db(db)
        logger.info(
            "[drive/conciliacion_sheet] Sync programado OK filas=%s drive_filas=%s run_id=%s",
            res.get("row_count"),
            res.get("drive_rows"),
            res.get("run_id"),
        )
    except ValueError as e:
        logger.warning(
            "[drive/conciliacion_sheet] Sync programado omitido o no configurado: %s",
            e,
        )
    except Exception as e:
        logger.exception("[drive/conciliacion_sheet] Sync programado error: %s", e)
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
    """Cron 4:00, 11:00 y 20:00 (America/Caracas): pipeline Gmail correos sin estrella y sin etiquetas IMAGEN 1/2/3."""
    from datetime import datetime, timedelta

    from sqlalchemy import and_, select

    if not getattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", False):
        return
    db = SessionLocal()
    try:
        from app.models.pagos_gmail_sync import PagosGmailSync
        from app.services.pagos_gmail.pipeline import run_pipeline

        cutoff = datetime.utcnow() - timedelta(hours=2)
        row = db.execute(
            select(PagosGmailSync).where(
                and_(
                    PagosGmailSync.status == "running",
                    PagosGmailSync.started_at >= cutoff,
                )
            ).limit(1)
        ).scalars().first()
        if row is not None:
            logger.info("[PAGOS_GMAIL] Escaneo programado omitido: sync en curso")
            return
        logger.info("[PAGOS_GMAIL] Escaneo programado: pending_identification")
        run_pipeline(db, existing_sync_id=None, scan_filter="pending_identification")
    except Exception as e:
        logger.exception("[PAGOS_GMAIL] Escaneo programado: %s", e)
    finally:
        db.close()


def start_scheduler() -> None:
    """Inicia el scheduler: finiquito 02:00 diario; caché Diferencia abono domingo 02:00 (opcional); caché Q vs aprobación domingo 02:03 (opcional); auditoria 03:00; notif 2 dias antes 03:00 (opcional por BD); hoja Drive 04:01; limpieza 04:00; Gmail 04/11/20 opcional."""
    global _scheduler
    if _scheduler is not None:
        logger.warning("Scheduler ya estÃ¡ iniciado.")
        return
    _scheduler = BackgroundScheduler(timezone=SCHEDULER_TZ)
    _scheduler.add_job(
        _job_finiquito_refresh,
        CronTrigger(hour=2, minute=0, timezone=SCHEDULER_TZ),
        id="finiquito_refresh_0200",
        name="Finiquito: refrescar casos 02:00",
    )
    if getattr(settings, "ENABLE_ABONOS_DRIVE_CACHE_NIGHTLY", True):
        _scheduler.add_job(
            _job_abonos_drive_cuotas_cache_0200,
            CronTrigger(day_of_week="sun", hour=2, minute=0, timezone=SCHEDULER_TZ),
            id="abonos_drive_cuotas_cache_dom_0200",
            name="Notificaciones: caché Diferencia abono (hoja vs cuotas) domingo 02:00",
        )
    if getattr(settings, "ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY", True):
        _scheduler.add_job(
            _job_fecha_entrega_q_aprobacion_cache_0203,
            CronTrigger(day_of_week="sun", hour=2, minute=3, timezone=SCHEDULER_TZ),
            id="fecha_entrega_q_aprobacion_cache_dom_0203",
            name="Notificaciones: caché columna Q vs fecha_aprobacion domingo 02:03",
        )

    _scheduler.add_job(
        _job_auditoria_cartera_prestamos,
        CronTrigger(hour=3, minute=0, timezone=SCHEDULER_TZ),
        id="auditoria_cartera_prestamos_0300",
        name="Auditoria cartera prestamos 03:00",
    )
    _scheduler.add_job(
        _job_notificaciones_pago_2_dias_antes_0300,
        CronTrigger(hour=3, minute=0, timezone=SCHEDULER_TZ),
        id="notificaciones_pago_2_dias_antes_0300",
        name="Notificaciones 2 dias antes (PAGO_2_DIAS_ANTES_PENDIENTE) 03:00",
    )
    # 04:01 - Snapshot Google CONCILIACIÓN -> conciliacion_sheet_* + tabla drive (A..S)
    _scheduler.add_job(
        _job_hoja_drive_conciliacion_sync,
        CronTrigger(hour=4, minute=1, timezone=SCHEDULER_TZ),
        id="hoja_drive_conciliacion_0401",
        name="Hoja Drive CONCILIACION (A:S) 04:01",
    )
    # 4:00 - Limpieza de cÃ³digos de estado de cuenta (expirados o usados > 24 h)
    _scheduler.add_job(
        _job_limpiar_estado_cuenta_codigos,
        CronTrigger(hour=4, minute=0, timezone=SCHEDULER_TZ),
        id="limpiar_estado_cuenta_codigos",
        name="Limpiar cÃ³digos estado de cuenta 4:00",
    )
    _gmail_log = ""
    if getattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", False):
        for _h, _jid, _label in (
            (4, "pagos_gmail_pending_scan_0400", "4:00"),
            (11, "pagos_gmail_pending_scan_1100", "11:00"),
            (20, "pagos_gmail_pending_scan_2000", "20:00"),
        ):
            _scheduler.add_job(
                _job_pagos_gmail_pending_scan,
                CronTrigger(hour=_h, minute=0, timezone=SCHEDULER_TZ),
                id=_jid,
                name=f"Gmail Pagos pendientes {_label}",
            )
        _gmail_log = "; Gmail pagos pendientes 4:00, 11:00 y 20:00"
    _scheduler.start()
    _caches_notif_log = ""
    if getattr(settings, "ENABLE_ABONOS_DRIVE_CACHE_NIGHTLY", True):
        _caches_notif_log += "; caché Diferencia abono domingo 02:00"
    if getattr(settings, "ENABLE_FECHA_ENTREGA_Q_CACHE_NIGHTLY", True):
        _caches_notif_log += "; caché Q vs aprobación domingo 02:03"
    logger.info(
        "Scheduler iniciado: finiquito 02:00%s; auditoria 03:00; notif PAGO_2_DIAS_ANTES 03:00 (si habilitado en BD); "
        "hoja Drive CONCILIACION 04:01; limpieza estado_cuenta_codigos 4:00%s (%s).",
        _caches_notif_log,
        _gmail_log,
        SCHEDULER_TZ,
    )
    if getattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", False):
        for _gjid in (
            "pagos_gmail_pending_scan_0400",
            "pagos_gmail_pending_scan_1100",
            "pagos_gmail_pending_scan_2000",
        ):
            _gj = _scheduler.get_job(_gjid)
            if _gj is not None:
                logger.info(
                    "[PAGOS_GMAIL] Job %s proxima_ejecucion=%s (referencia tz=%s)",
                    _gjid,
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
