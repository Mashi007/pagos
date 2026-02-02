"""
Scheduler para tareas programadas. Reportes de cobranzas a las 6:00 y 13:00.
Usa APScheduler con sesión de BD (get_db pattern) para actualizar reportes.
"""
import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import SessionLocal
from app.api.v1.endpoints import cobranzas

logger = logging.getLogger(__name__)

# Zona horaria por defecto (Venezuela). Configurable vía env si se añade SCHEDULER_TZ.
SCHEDULER_TZ = "America/Caracas"

_scheduler: Optional[BackgroundScheduler] = None


def _job_actualizar_reportes_cobranzas() -> None:
    """
    Job que se ejecuta a las 6:00 y 13:00. Actualiza reportes de cobranzas
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


def start_scheduler() -> None:
    """Inicia el scheduler con los cron 6:00 y 13:00 para reportes de cobranzas."""
    global _scheduler
    if _scheduler is not None:
        logger.warning("Scheduler ya está iniciado.")
        return
    _scheduler = BackgroundScheduler(timezone=SCHEDULER_TZ)
    _scheduler.add_job(
        _job_actualizar_reportes_cobranzas,
        CronTrigger(hour=6, minute=0, timezone=SCHEDULER_TZ),
        id="reportes_cobranzas_6am",
        name="Actualizar reportes cobranzas 6:00",
    )
    _scheduler.add_job(
        _job_actualizar_reportes_cobranzas,
        CronTrigger(hour=13, minute=0, timezone=SCHEDULER_TZ),
        id="reportes_cobranzas_1pm",
        name="Actualizar reportes cobranzas 13:00",
    )
    _scheduler.start()
    logger.info(
        "Scheduler iniciado: reportes cobranzas a las 6:00 y 13:00 (%s).",
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
