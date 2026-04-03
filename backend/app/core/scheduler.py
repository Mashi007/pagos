"""
Scheduler para tareas programadas (zona America/Caracas).

- 01:10  Emails credito liquidado: PDF estado de cuenta (dias 1 y 2 despues de fecha_liquidado).
- 02:00  Finiquito: refrescar tabla finiquito_casos.
- 03:00  Auditoria cartera: evaluacion de prestamos y metadatos en configuracion.
- 04:00  Limpieza codigos estado de cuenta.
- 04:00, 11:00, 20:00  Gmail pagos pendientes (si esta habilitado; America/Caracas).

Reportes cobranzas, informe de pagos por email y campanas CRM programadas ya no se disparan por scheduler; bajo demanda o manual.
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

    if not getattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", True):
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
    """Inicia el scheduler: liquidado 01:10; finiquito 02:00; auditoria 03:00; limpieza 04:00; Gmail 04/11/20 opcional."""
    global _scheduler
    if _scheduler is not None:
        logger.warning("Scheduler ya estÃ¡ iniciado.")
        return
    _scheduler = BackgroundScheduler(timezone=SCHEDULER_TZ)
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

    _scheduler.add_job(
        _job_auditoria_cartera_prestamos,
        CronTrigger(hour=3, minute=0, timezone=SCHEDULER_TZ),
        id="auditoria_cartera_prestamos_0300",
        name="Auditoria cartera prestamos 03:00",
    )
    # 4:00 - Limpieza de cÃ³digos de estado de cuenta (expirados o usados > 24 h)
    _scheduler.add_job(
        _job_limpiar_estado_cuenta_codigos,
        CronTrigger(hour=4, minute=0, timezone=SCHEDULER_TZ),
        id="limpiar_estado_cuenta_codigos",
        name="Limpiar cÃ³digos estado de cuenta 4:00",
    )
    _gmail_log = ""
    if getattr(settings, "PAGOS_GMAIL_SCHEDULED_SCAN_ENABLED", True):
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
    logger.info(
        "Scheduler iniciado: liquidado PDF 01:10; finiquito 02:00; auditoria 03:00; limpieza estado_cuenta_codigos 4:00%s (%s).",
        _gmail_log,
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
