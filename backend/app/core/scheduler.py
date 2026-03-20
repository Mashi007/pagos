"""
Scheduler para tareas programadas (zona America/Caracas).

ActualizaciÃ³n periÃ³dica de informes y reportes:
- 01:00  Reportes cobranzas (resumen + diagnÃ³stico).
- 02:00  Notificaciones (actualizar mora / datos para seguimiento).
- 06:00  Informe de pagos por email (link Google Sheet).
- 13:00  Reportes cobranzas.
- 13:00  Informe de pagos por email.
- 16:00  CachÃ© dashboard (hilo aparte en main: 1:00, 13:00).
- 16:30  Informe de pagos por email.
- 23:00  EnvÃ­o automÃ¡tico de notificaciones (previas, dÃ­a pago, retrasadas, prejudicial, mora 90).

Los informes de Cobranzas (clientes atrasados, rendimiento analista, montos por mes, etc.)
se generan bajo demanda al solicitar JSON/PDF/Excel; no se precalculan.
"""
import logging
import threading
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.database import SessionLocal
from app.scripts.aplicar_pagos_pendientes_job import aplicar_pagos_pendientes
from app.api.v1.endpoints import cobranzas, notificaciones, notificaciones_tabs
from app.api.v1.endpoints.pagos_gmail import _is_pipeline_running, _last_run_too_recent, _run_pipeline_background
from app.models.pagos_gmail_sync import PagosGmailSync

logger = logging.getLogger(__name__)

# Zona horaria por defecto (Venezuela). Configurable vÃ­a env si se aÃ±ade SCHEDULER_TZ.
SCHEDULER_TZ = "America/Caracas"

_scheduler: Optional[BackgroundScheduler] = None


def _job_actualizar_notificaciones() -> None:
    """Job 2:00. ActualizaciÃ³n de notificaciones (mora desde cuotas)."""
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


def _job_envio_notificaciones_23() -> None:
    """Job 23:00. EnvÃ­o automÃ¡tico de todas las notificaciones solo en producciÃ³n. En modo pruebas el envÃ­o es solo manual."""
    db = SessionLocal()
    try:
        config = notificaciones.get_notificaciones_envios_config(db)
        if config.get("modo_pruebas") is True:
            logger.info("EnvÃ­o notificaciones 23:00: omitido (modo pruebas activo; envÃ­o solo manual).")
            return
        result = notificaciones_tabs.ejecutar_envio_todas_notificaciones(db)
        logger.info(
            "EnvÃ­o notificaciones 23:00: enviados=%s fallidos=%s sin_email=%s omitidos_config=%s whatsapp_ok=%s whatsapp_fail=%s",
            result.get("enviados", 0),
            result.get("fallidos", 0),
            result.get("sin_email", 0),
            result.get("omitidos_config", 0),
            result.get("enviados_whatsapp", 0),
            result.get("fallidos_whatsapp", 0),
        )
    except Exception as e:
        logger.exception("Error en job envio_notificaciones_23: %s", e)
    finally:
        db.close()


def _job_actualizar_reportes_cobranzas() -> None:
    """
    Job que se ejecuta a las 1:00 y 13:00. Actualiza reportes de cobranzas
    (resumen + diagnÃ³stico) usando sesiÃ³n de BD.
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
    """Job que envÃ­a email con link a Google Sheet del informe de pagos (6:00, 13:00, 16:30)."""
    try:
        from app.core.informe_pagos_email import enviar_informe_pagos_email
        enviar_informe_pagos_email()
    except Exception as e:
        logger.exception("Error en job informe_pagos_email: %s", e)



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


def _job_campanas_programadas() -> None:
    """Job cada minuto. Ejecuta campaÃ±as CRM en estado programada cuya prÃ³xima ejecuciÃ³n ya llegÃ³."""
    try:
        from app.api.v1.endpoints import crm_campanas
        crm_campanas.ejecutar_campanas_programadas()
    except Exception as e:
        logger.exception("Error en job campanas_programadas: %s", e)


def _job_pagos_gmail_pipeline() -> None:
    """Job cada N min (PAGOS_GMAIL_CRON_MINUTES): procesa correos (Gmail -> Drive -> Gemini -> Sheets). No procesa si aÃºn no es tiempo desde la Ãºltima ejecuciÃ³n."""
    db = SessionLocal()
    try:
        if _is_pipeline_running(db):
            logger.info("Pagos Gmail pipeline: omitido (ya hay una ejecucion en curso)")
            return
        too_recent, wait_min = _last_run_too_recent(db)
        if too_recent and wait_min is not None:
            logger.info("Pagos Gmail pipeline: omitido (aun no es tiempo, esperar %d min)", wait_min)
            return
        sync = PagosGmailSync(status="running", emails_processed=0, files_processed=0)
        db.add(sync)
        db.commit()
        db.refresh(sync)
        sync_id = sync.id
        thread = threading.Thread(target=_run_pipeline_background, args=(sync_id, "unread"), daemon=True)
        thread.start()
        logger.info("Pagos Gmail pipeline: lanzado en segundo plano sync_id=%s (solo no leidos)", sync_id)
    except Exception as e:
        logger.exception("Error en job pagos_gmail_pipeline: %s", e)
    finally:
        db.close()



def start_scheduler() -> None:
    """Inicia el scheduler: notificaciones 2:00; envÃ­o notificaciones 23:00; cobranzas 1:00 y 13:00; informe pagos 6:00, 13:00 y 16:30."""
    global _scheduler
    if _scheduler is not None:
        logger.warning("Scheduler ya estÃ¡ iniciado.")
        return
    _scheduler = BackgroundScheduler(timezone=SCHEDULER_TZ)
    # 2:00 - Actualizar datos de notificaciones (mora desde cuotas)
    _scheduler.add_job(
        _job_actualizar_notificaciones,
        CronTrigger(hour=2, minute=0, timezone=SCHEDULER_TZ),
        id="notificaciones_2am",
        name="Actualizar notificaciones 2:00",
    )
    # 23:00 - EnvÃ­o automÃ¡tico de notificaciones (emails/WhatsApp por tipo)
    _scheduler.add_job(
        _job_envio_notificaciones_23,
        CronTrigger(hour=23, minute=0, timezone=SCHEDULER_TZ),
        id="envio_notificaciones_11pm",
        name="EnvÃ­o notificaciones 23:00",
    )
    # 1:00 y 13:00 - Reportes cobranzas (actualizaciÃ³n automÃ¡tica de informes)
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
    # 4:00 - Limpieza de cÃ³digos de estado de cuenta (expirados o usados > 24 h)
    _scheduler.add_job(
        _job_limpiar_estado_cuenta_codigos,
        CronTrigger(hour=4, minute=0, timezone=SCHEDULER_TZ),
        id="limpiar_estado_cuenta_codigos",
        name="Limpiar cÃ³digos estado de cuenta 4:00",
    )
    # CampaÃ±as CRM programadas: cada 1 minuto revisar si hay que enviar
    _scheduler.add_job(
        _job_campanas_programadas,
        IntervalTrigger(minutes=1),
        id="campanas_crm_programadas",
        name="CampaÃ±as CRM programadas (cada 1 min)",
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
    
    

    # Aplicar pagos pendientes a cuotas: solo en el scheduler del worker lider (ver main.py).
    # Evita dos BackgroundScheduler disparando el mismo job con varios workers Uvicorn.
    _scheduler.add_job(
        aplicar_pagos_pendientes,
        IntervalTrigger(minutes=3),
        id="aplicar_pagos_pendientes",
        name="Aplicar pagos pendientes (cada 3 min)",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )
    _scheduler.start()
    logger.info(
        "Scheduler iniciado: aplicar_pagos_pendientes cada 3 min; notificaciones 2:00; envÃ­o notificaciones 23:00; cobranzas 1:00 y 13:00; informe pagos 6:00, 13:00 y 16:30; limpieza estado_cuenta_codigos 4:00 (%s).",
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
