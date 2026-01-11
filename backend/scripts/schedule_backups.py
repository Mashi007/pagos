#!/usr/bin/env python3
"""
Programar backups automáticos usando APScheduler

Este script puede ejecutarse como servicio independiente o integrarse
en la aplicación principal usando APScheduler.

Uso:
    python scripts/schedule_backups.py

Variables de entorno:
    DATABASE_URL: URL de conexión a PostgreSQL
    BACKUP_DIR: Directorio donde guardar backups
    BACKUP_RETENTION_DAYS: Días de retención (default: 30)
    BACKUP_SCHEDULE_HOUR: Hora del día para backup (default: 2 AM)
"""

import logging
import os
import signal
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Importar función de backup
from backup_database import create_backup, cleanup_old_backups, get_database_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = BlockingScheduler()


def run_backup():
    """Ejecutar backup programado"""
    try:
        database_url = get_database_url()
        backup_dir = os.getenv("BACKUP_DIR", "./backups")
        retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

        logger.info(f"🔄 Ejecutando backup programado a las {datetime.now()}")

        # Crear backup
        backup_file = create_backup(database_url, backup_dir)

        # Limpiar backups antiguos
        cleanup_old_backups(backup_dir, retention_days)

        logger.info(f"✅ Backup programado completado: {backup_file}")

    except Exception as e:
        logger.error(f"❌ Error en backup programado: {e}")


def signal_handler(sig, frame):
    """Manejar señales para shutdown graceful"""
    logger.info("🛑 Recibida señal de terminación. Cerrando scheduler...")
    scheduler.shutdown()
    sys.exit(0)


def main():
    """Función principal"""
    # Configurar handlers de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Obtener hora de backup desde variable de entorno (default: 2 AM)
    backup_hour = int(os.getenv("BACKUP_SCHEDULE_HOUR", "2"))

    logger.info("=" * 60)
    logger.info("📅 PROGRAMADOR DE BACKUPS INICIADO")
    logger.info("=" * 60)
    logger.info(f"⏰ Backups programados diariamente a las {backup_hour}:00")
    logger.info("Presiona Ctrl+C para detener")

    # Programar backup diario
    scheduler.add_job(
        run_backup,
        trigger=CronTrigger(hour=backup_hour, minute=0),
        id="daily_backup",
        name="Backup diario de base de datos",
        replace_existing=True,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Scheduler detenido")


if __name__ == "__main__":
    main()
