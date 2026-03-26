"""
Scheduler para tareas programadas (zona America/Caracas).

ActualizaciÃ³n periÃ³dica de informes y reportes:
- 01:00  Reportes cobranzas (resumen + diagnÃ³stico).
- 00:50  Notificaciones (actualizar mora / datos; antes de envios por hora configurada).
- 06:00  Informe de pagos por email (link Google Sheet).
- 13:00  Reportes cobranzas.
- 13:00  Informe de pagos por email.
- 16:00  CachÃ© dashboard (hilo aparte en main: 1:00, 13:00).
- 16:30  Informe de pagos por email.
- * cada 15 min (:00,:15,:30,:45)  Envio automatico por hora configurada (programador en notificaciones_envios; America/Caracas).
- 01:10  Emails credito liquidado: PDF estado de cuenta (dias 1 y 2 despues de fecha_liquidado; America/Caracas).
- 02:00  Finiquito: refrescar tabla finiquito_casos (total_financiamiento = sum cuotas.total_pagado exacto).

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
from app.api.v1.endpoints import cobranzas, notificaciones
from app.services.notificaciones_envios_store import coerce_modo_pruebas_notificaciones
from app.services.notificaciones_envio_batch_resumen import persist_ultimo_envio_batch
from app.api.v1.endpoints.pagos_gmail import _is_pipeline_running, _last_run_too_recent, _run_pipeline_background
from app.models.pagos_gmail_sync import PagosGmailSync

logger = logging.getLogger(__name__)

# Zona horaria por defecto (Venezuela). Configurable vÃ­a env si se aÃ±ade SCHEDULER_TZ.
SCHEDULER_TZ = "America/Caracas"

_scheduler: Optional[BackgroundScheduler] = None


def _job_actualizar_notificaciones() -> None:
    """Job 00:50. Actualizacion de notificaciones (mora desde cuotas), antes del envio 01:00."""
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


def _job_emails_liquidado_diferidos() -> None:
    """Job 01:10. Correos con PDF estado de cuenta para prestamos LIQUIDADO (N dias despues de fecha_liquidado)."""
    db = SessionLocal()
    try:
        from app.services.liquidado_email_deferido import ejecutar_emails_liquidado_diferidos

        res = ejecutar_emails_liquidado_diferidos(db)
        logger.info(
            "Emails liquidado diferido: enviados_ok=%s fallidos=%s omitidos_dup=%s dias=%s",
            res.get("enviados_ok"),
            res.get("fallidos"),
            res.get("omitidos_duplicado"),
            res.get("dias_config"),
        )
    except Exception as e:
        logger.exception("Error en job emails_liquidado_diferidos: %s", e)
    finally:
        db.close()


def _job_envio_notificaciones_programador() -> None:
    """
    Cada 15 minutos en Caracas (:00, :15, :30, :45): envia los criterios cuya hora
    en configuracion coincide con la hora actual (programador por tipo). Una vez por dia por criterio.
    La hora del programador debe usar minuto 0, 15, 30 o 45 para coincidir con una corrida.
    """
    db = SessionLocal()
    try:
        config = notificaciones.get_notificaciones_envios_config(db)
        if coerce_modo_pruebas_notificaciones(config.get("modo_pruebas")):
            logger.debug("Envio notificaciones programador: omitido (modo pruebas; envio manual).")
            return
        from app.services.notificaciones_programador import ejecutar_envios_por_programador

        result = ejecutar_envios_por_programador(db)
        if result.get("skipped"):
            logger.debug(
                "Envio notificaciones programador: sin coincidencia de hora (%s).",
                result.get("motivo") or result.get("hm_caracas"),
            )
            return
        if not result.get("detalles"):
            return
        persist_ultimo_envio_batch(db, resultado=result, origen="scheduler_programador")
        db.commit()
        logger.info(
            "Envio notificaciones programador %s: enviados=%s fallidos=%s sin_email=%s omitidos_config=%s omitidos_paquete=%s whatsapp_ok=%s whatsapp_fail=%s",
            result.get("hm_caracas"),
            result.get("enviados", 0),
            result.get("fallidos", 0),
            result.get("sin_email", 0),
            result.get("omitidos_config", 0),
            result.get("omitidos_paquete_incompleto", 0),
            result.get("enviados_whatsapp", 0),
            result.get("fallidos_whatsapp", 0),
        )
    except Exception as e:
        logger.exception("Error en job envio_notificaciones_programador: %s", e)
        try:
            db.rollback()
            persist_ultimo_envio_batch(
                db, resultado={}, origen="scheduler_programador", error=str(e)[:5000]
            )
            db.commit()
        except Exception:
            db.rollback()
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



def _job_finiquito_refresh() -> None:
    """Job 02:00. Rellena/actualiza finiquito_casos (prestamos con suma total_pagado = total_financiamiento)."""
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
    """Inicia el scheduler: notificaciones 00:50 + envio programador cada 15 min; liquidado+PDF 01:10; cobranzas 1:00 y 13:00; informe pagos 6:00, 13:00 y 16:30."""
    global _scheduler
    if _scheduler is not None:
        logger.warning("Scheduler ya estÃ¡ iniciado.")
        return
    _scheduler = BackgroundScheduler(timezone=SCHEDULER_TZ)
    # 00:50 - Actualizar datos de notificaciones (mora desde cuotas), antes de envios por hora
    _scheduler.add_job(
        _job_actualizar_notificaciones,
        CronTrigger(hour=0, minute=50, timezone=SCHEDULER_TZ),
        id="notificaciones_0050",
        name="Actualizar notificaciones 00:50",
    )
    # Cada minuto: envio por hora configurada (programador) en notificaciones_envios
    _scheduler.add_job(
        _job_envio_notificaciones_programador,
        CronTrigger(minute="*", timezone=SCHEDULER_TZ),
        id="envio_notificaciones_programador",
        name="Envio notificaciones por programador (cada minuto)",
    )
    _scheduler.add_job(
        _job_emails_liquidado_diferidos,
        CronTrigger(hour=1, minute=10, timezone=SCHEDULER_TZ),
        id="emails_liquidado_diferidos_0110",
        name="Emails liquidado + PDF estado cuenta 01:10",
    )
    _scheduler.add_job(
        _job_finiquito_refresh,
        CronTrigger(hour=2, minute=0, timezone=SCHEDULER_TZ),
        id="finiquito_refresh_0200",
        name="Finiquito: refrescar casos 02:00",
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

    _scheduler.start()
    logger.info(
        "Scheduler iniciado: notificaciones 00:50 + programador cada minuto; liquidado PDF 01:10; finiquito 02:00; cobranzas 1:00 y 13:00; informe pagos 6:00, 13:00 y 16:30; limpieza estado_cuenta_codigos 4:00 (%s).",
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
