#!/usr/bin/env python3
"""
Script de backup automático de la base de datos PostgreSQL
Puede ejecutarse manualmente o programarse con APScheduler

Uso:
    python scripts/backup_database.py

Variables de entorno requeridas:
    DATABASE_URL: URL de conexión a PostgreSQL
    BACKUP_DIR: Directorio donde guardar backups (opcional, default: ./backups)
    BACKUP_RETENTION_DAYS: Días de retención de backups (opcional, default: 30)
"""

import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Obtener DATABASE_URL desde variable de entorno"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL no está configurado como variable de entorno")
    return database_url


def parse_database_url(url: str) -> dict:
    """
    Parsear URL de PostgreSQL para obtener componentes
    Formato: postgresql://user:password@host:port/database
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return {
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": parsed.path.lstrip("/"),
    }


def create_backup_dir(backup_dir: str) -> Path:
    """Crear directorio de backups si no existe"""
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)
    return backup_path


def generate_backup_filename(database_name: str) -> str:
    """Generar nombre de archivo de backup con timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{database_name}_backup_{timestamp}.sql"


def create_backup(database_url: str, backup_dir: str) -> Path:
    """
    Crear backup de la base de datos usando pg_dump

    Args:
        database_url: URL de conexión a PostgreSQL
        backup_dir: Directorio donde guardar el backup

    Returns:
        Path al archivo de backup creado
    """
    try:
        db_info = parse_database_url(database_url)
        backup_path = create_backup_dir(backup_dir)
        backup_filename = generate_backup_filename(db_info["database"])
        backup_file = backup_path / backup_filename

        logger.info(f"🔄 Creando backup de {db_info['database']}...")

        # Construir comando pg_dump
        # Usar PGPASSWORD para evitar prompt de contraseña
        env = os.environ.copy()
        if db_info["password"]:
            env["PGPASSWORD"] = db_info["password"]

        cmd = [
            "pg_dump",
            "-h",
            db_info["host"],
            "-p",
            str(db_info["port"]),
            "-U",
            db_info["user"],
            "-d",
            db_info["database"],
            "-F",
            "c",  # Formato custom (comprimido)
            "-f",
            str(backup_file),
        ]

        # Ejecutar pg_dump
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        # Verificar que el archivo se creó
        if backup_file.exists() and backup_file.stat().st_size > 0:
            file_size_mb = backup_file.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Backup creado exitosamente: {backup_file}")
            logger.info(f"📦 Tamaño del backup: {file_size_mb:.2f} MB")
            return backup_file
        else:
            raise Exception("El archivo de backup no se creó o está vacío")

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error al crear backup: {e.stderr}")
        raise
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        raise


def cleanup_old_backups(backup_dir: str, retention_days: int = 30):
    """
    Eliminar backups antiguos según días de retención

    Args:
        backup_dir: Directorio de backups
        retention_days: Días de retención (default: 30)
    """
    from datetime import timedelta

    backup_path = Path(backup_dir)
    if not backup_path.exists():
        return

    cutoff_date = datetime.now() - timedelta(days=retention_days)
    deleted_count = 0

    for backup_file in backup_path.glob("*.sql"):
        try:
            # Obtener fecha de modificación del archivo
            file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            if file_mtime < cutoff_date:
                backup_file.unlink()
                deleted_count += 1
                logger.info(f"🗑️ Backup antiguo eliminado: {backup_file.name}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo eliminar {backup_file.name}: {e}")

    if deleted_count > 0:
        logger.info(f"✅ {deleted_count} backups antiguos eliminados")


def main():
    """Función principal"""
    try:
        # Obtener configuración desde variables de entorno
        database_url = get_database_url()
        backup_dir = os.getenv("BACKUP_DIR", "./backups")
        retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

        logger.info("=" * 60)
        logger.info("🔄 INICIANDO BACKUP DE BASE DE DATOS")
        logger.info("=" * 60)

        # Crear backup
        backup_file = create_backup(database_url, backup_dir)

        # Limpiar backups antiguos
        cleanup_old_backups(backup_dir, retention_days)

        logger.info("=" * 60)
        logger.info("✅ BACKUP COMPLETADO EXITOSAMENTE")
        logger.info("=" * 60)
        logger.info(f"📁 Archivo: {backup_file}")
        logger.info(f"📅 Retención: {retention_days} días")

        return 0

    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ ERROR AL CREAR BACKUP")
        logger.error("=" * 60)
        logger.error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
