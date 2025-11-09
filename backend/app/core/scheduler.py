"""
Scheduler para tareas automáticas
Usa APScheduler para ejecutar tareas programadas
"""

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# Instancia global del scheduler
scheduler = BackgroundScheduler(daemon=True)


def calcular_notificaciones_previas_job():
    """Job que calcula notificaciones previas a las 2 AM"""
    db = SessionLocal()
    try:
        from app.services.notificaciones_previas_service import NotificacionesPreviasService
        
        logger.info("🔄 [Scheduler] Iniciando cálculo de notificaciones previas...")
        service = NotificacionesPreviasService(db)
        resultados = service.calcular_notificaciones_previas()
        
        logger.info(
            f"✅ [Scheduler] Notificaciones previas calculadas: {len(resultados)} registros "
            f"(5 días: {len([r for r in resultados if r['dias_antes_vencimiento'] == 5])}, "
            f"3 días: {len([r for r in resultados if r['dias_antes_vencimiento'] == 3])}, "
            f"1 día: {len([r for r in resultados if r['dias_antes_vencimiento'] == 1])})"
        )
        
    except Exception as e:
        logger.error(f"❌ [Scheduler] Error calculando notificaciones previas: {e}", exc_info=True)
    finally:
        db.close()


def iniciar_scheduler():
    """Inicia el scheduler con todas las tareas programadas"""
    try:
        # Agregar job para notificaciones previas (2 AM diariamente)
        scheduler.add_job(
            calcular_notificaciones_previas_job,
            trigger=CronTrigger(hour=2, minute=0),  # 2:00 AM todos los días
            id="notificaciones_previas",
            name="Calcular Notificaciones Previas",
            replace_existing=True,
        )
        
        # Iniciar scheduler
        scheduler.start()
        logger.info("✅ Scheduler iniciado correctamente")
        logger.info("📅 Job 'notificaciones_previas' programado para ejecutarse diariamente a las 2:00 AM")
        
    except Exception as e:
        logger.error(f"❌ Error iniciando scheduler: {e}", exc_info=True)


def detener_scheduler():
    """Detiene el scheduler"""
    try:
        if scheduler.running:
            scheduler.shutdown()
            logger.info("✅ Scheduler detenido correctamente")
    except Exception as e:
        logger.error(f"❌ Error deteniendo scheduler: {e}", exc_info=True)

