"""
Scheduler para tareas programadas (zona America/Caracas).

Actualización periódica de informes y reportes:
- 01:00  Reportes cobranzas (resumen + diagnóstico).
- 02:00  Notificaciones (actualizar mora / datos para seguimiento).
- 06:00  Informe de pagos por email (link Google Sheet).
- 13:00  Reportes cobranzas.
- 13:00  Informe de pagos por email.
- 16:00  Caché dashboard (hilo aparte en main: 1:00, 13:00).
- 16:30  Informe de pagos por email.

Los informes de Cobranzas (clientes atrasados, rendimiento analista, montos por mes, etc.)
se generan bajo demanda al solicitar JSON/PDF/Excel; no se precalculan.
"""
import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.database import SessionLocal
from app.api.v1.endpoints import cobranzas, notificaciones

logger = logging.getLogger(__name__)

# Zona horaria por defecto (Venezuela). Configurable vía env si se añade SCHEDULER_TZ.
SCHEDULER_TZ = "America/Caracas"

_scheduler: Optional[BackgroundScheduler] = None


def _job_actualizar_notificaciones() -> None:
    """Job 2:00. Actualización de notificaciones (mora desde cuotas)."""
    db = SessionLocal()
    try:
        result = notificaciones.ejecutar_actualizacion_notificaciones(db)
        logger.info(
            "Notificaciones actualizadas: %s",
            result.get("clientes_actualizados", 0),
        )
    except Exception as e:
        logger.exception("Error en job actualizar_notificaciones: %s", e)
    finally:
        db.close()


def _job_actualizar_reportes_cobranzas() -> None:
    """
    Job que se ejecuta a las 1:00 y 13:00. Actualiza reportes de cobranzas
    (resumen + diagnóstico) usando sesión de BD.
    """
    db = SessionLocal()
    try:
        resumen = cobranzas.ejecutar_actualizacion_reportes(db)
        logger.info(
            "Reportes cobranzas actualizados: cuotas_vencidas=%s monto_adeudado=%s clientes_atrasados=%s",
            resumen.get("total_cuotas_vencidas"),
            resumen.get("monto_total_adeudado"),
            resumen.get("clientes_atrasados"),
        )
    except Exception as e:
        logger.exception("Error en job actualizar_reportes_cobranzas: %s", e)
    finally:
        db.close()


def _job_informe_pagos_email() -> None:
    """Job que envía email con link a Google Sheet del informe de pagos (6:00, 13:00, 16:30)."""
    try:
        from app.core.informe_pagos_email import enviar_informe_pagos_email
        enviar_informe_pagos_email()
    except Exception as e:
        logger.exception("Error en job informe_pagos_email: %s", e)



def _job_pagos_gmail_pipeline() -> None:
    """Job cada N min (PAGOS_GMAIL_CRON_MINUTES): procesa correos (Gmail -> Drive -> Gemini -> Sheets). No procesa si aún no es tiempo desde la última ejecución."""
    db = SessionLocal()
    try:
        from app.api.v1.endpoints.pagos_gmail import _is_pipeline_running, _last_run_too_recent
        from app.services.pagos_gmail.pipeline import run_pipeline
        if _is_pipeline_running(db):
            logger.info("Pagos Gmail pipeline: omitido (ya hay una ejecucion en curso)")
            return
        too_recent, wait_min = _last_run_too_recent(db)
        if too_recent and wait_min is not None:
            logger.info("Pagos Gmail pipeline: omitido (aun no es tiempo, esperar %d min)", wait_min)
            return
        sync_id, status = run_pipeline(db)
        logger.info("Pagos Gmail pipeline: sync_id=%s status=%s", sync_id, status)
    except Exception as e:
        logger.exception("Error en job pagos_gmail_pipeline: %s", e)
    finally:
        db.close()



def start_scheduler() -> None:
    """Inicia el scheduler: notificaciones 2:00; cobranzas 1:00 y 13:00; informe pagos 6:00, 13:00 y 16:30."""
    global _scheduler
    if _scheduler is not None:
        logger.warning("Scheduler ya está iniciado.")
        return
    _scheduler = BackgroundScheduler(timezone=SCHEDULER_TZ)
    # 2:00 - Notificaciones
    _scheduler.add_job(
        _job_actualizar_notificaciones,
        CronTrigger(hour=2, minute=0, timezone=SCHEDULER_TZ),
        id="notificaciones_2am",
        name="Actualizar notificaciones 2:00",
    )
    # 1:00 y 13:00 - Reportes cobranzas (actualización automática de informes)
    _scheduler.add_job(
        _job_actualizar_reportes_cobranzas,
        CronTrigger(hour=1, minute=0, timezone=SCHEDULER_TZ),
        id="reportes_cobranzas_1am",
        name="Actualizar reportes cobranzas 1:00",
    )
    _scheduler.add_job(
        _job_actualizar_reportes_cobranzas,
        CronTrigger(hour=13, minute=0, timezone=SCHEDULER_TZ),
        id="reportes_cobranzas_1pm",
        name="Actualizar reportes cobranzas 13:00",
    )
    # Informe de pagos: email con link a Google Sheet a las 6:00, 13:00 y 16:30
    _scheduler.add_job(
        _job_informe_pagos_email,
        CronTrigger(hour=6, minute=0, timezone=SCHEDULER_TZ),
        id="informe_pagos_6am",
        name="Email informe pagos 6:00",
    )
    _scheduler.add_job(
        _job_informe_pagos_email,
        CronTrigger(hour=13, minute=0, timezone=SCHEDULER_TZ),
        id="informe_pagos_1pm",
        name="Email informe pagos 13:00",
    )
    _scheduler.add_job(
        _job_informe_pagos_email,
        CronTrigger(hour=16, minute=30, timezone=SCHEDULER_TZ),
        id="informe_pagos_4h30",
        name="Email informe pagos 16:30",
    )
    # Pagos Gmail: intervalo desde PAGOS_GMAIL_CRON_MINUTES (por defecto 30 min; cuota Gemini free ~15 RPM)
    cron_min = settings.PAGOS_GMAIL_CRON_MINUTES
    _scheduler.add_job(
        _job_pagos_gmail_pipeline,
        IntervalTrigger(minutes=cron_min),
        id="pagos_gmail_pipeline",
        name=f"Pagos Gmail pipeline (cada {cron_min} min)",
    )
    logger.info("Pagos Gmail sync programado cada %d minutos (PAGOS_GMAIL_CRON_MINUTES=%d)", cron_min, cron_min)
    
    _scheduler.start()
    logger.info(
        "Scheduler iniciado: notificaciones 2:00; cobranzas 1:00 y 13:00; informe pagos 6:00, 13:00 y 16:30 (%s).",
        SCHEDULER_TZ,
    )


def stop_scheduler() -> None:
    """Detiene el scheduler (útil en tests o shutdown)."""
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("Scheduler detenido.")
