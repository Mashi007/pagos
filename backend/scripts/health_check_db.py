#!/usr/bin/env python
"""
Health check para verificar que la base de datos está lista y contiene todas las tablas requeridas.

Uso:
    python scripts/health_check_db.py

Retorna:
    - Código 0 si todo está bien
    - Código 1 si hay problemas
"""
import os
import sys
import time
import logging
from pathlib import Path

# Agregar backend al path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def check_database():
    """Verifica que la BD tiene todas las tablas requeridas."""
    try:
        from app.core.config import settings
        from sqlalchemy import create_engine, text, inspect
        
        logger.info(f"Conectando a: {settings.DATABASE_URL[:50]}...")
        
        # Preparar URL
        db_url = settings.DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        
        # Crear engine
        engine = create_engine(
            db_url,
            connect_args={"connect_timeout": 10},
            echo=False,
        )
        
        # Intentar conexión
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            if not result.fetchone():
                logger.error("❌ SELECT 1 falló")
                return False
        
        logger.info("✅ Conexión a BD verificada")
        
        # Verificar tablas críticas
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        CRITICAL_TABLES = [
            "clientes",
            "prestamos",
            "cuotas",
            "pagos_whatsapp",
            "tickets",
        ]
        
        missing = [t for t in CRITICAL_TABLES if t not in tables]
        
        if missing:
            logger.error(f"❌ Tablas faltantes: {missing}")
            logger.error(f"   Tablas disponibles: {tables}")
            return False
        
        logger.info(f"✅ Todas las tablas críticas existen: {CRITICAL_TABLES}")
        
        # Verificar acceso a tabla crítica
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM prestamos"))
            count = result.scalar()
            logger.info(f"✅ Tabla 'prestamos' accesible ({count} registros)")
        
        logger.info("=" * 60)
        logger.info("✅ HEALTH CHECK EXITOSO: Base de datos lista")
        logger.info("=" * 60)
        return True
        
    except Exception as e:
        logger.error(f"❌ HEALTH CHECK FALLÓ: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    success = check_database()
    sys.exit(0 if success else 1)
