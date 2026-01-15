#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para instalar la extensión pg_trgm en PostgreSQL.

Este script intenta instalar la extensión pg_trgm que es necesaria para
índices GIN optimizados en búsquedas de texto (especialmente con ILIKE).

REQUISITOS:
- Permisos de superusuario en PostgreSQL
- Si no tienes permisos, ejecuta manualmente con psql como superusuario
"""

import sys
import logging
import io
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar backend al path para imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import text
from app.db.session import SessionLocal

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verificar_extension():
    """Verifica si la extensión pg_trgm ya está instalada"""
    db = SessionLocal()
    try:
        query = text("""
            SELECT 
                extname AS nombre_extension,
                extversion AS version,
                n.nspname AS schema
            FROM pg_extension e
            JOIN pg_namespace n ON e.extnamespace = n.oid
            WHERE extname = 'pg_trgm'
        """)
        result = db.execute(query)
        row = result.fetchone()
        
        if row:
            logger.info("OK: Extension pg_trgm ya esta instalada")
            logger.info(f"   Version: {row.version}")
            logger.info(f"   Schema: {row.schema}")
            return True
        else:
            logger.info("NO: Extension pg_trgm NO esta instalada")
            return False
    except Exception as e:
        logger.error(f"ERROR: Error al verificar extension: {e}")
        return None
    finally:
        db.close()

def instalar_extension():
    """Intenta instalar la extensión pg_trgm"""
    db = SessionLocal()
    try:
        logger.info("Intentando instalar extension pg_trgm...")
        
        # Intentar crear la extensión
        query = text("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        db.execute(query)
        db.commit()
        
        logger.info("OK: Extension pg_trgm instalada correctamente")
        
        # Verificar instalación
        if verificar_extension():
            logger.info("OK: Verificacion exitosa: extension pg_trgm esta disponible")
            return True
        else:
            logger.warning("⚠️ La extensión se creó pero no se pudo verificar")
            return False
            
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ Error al instalar extensión: {error_msg}")
        
        if "permission denied" in error_msg.lower() or "must be superuser" in error_msg.lower():
            logger.error("")
            logger.error("=" * 70)
            logger.error("ADVERTENCIA: PERMISOS INSUFICIENTES")
            logger.error("=" * 70)
            logger.error("")
            logger.error("Este script requiere permisos de SUPERUSUARIO en PostgreSQL.")
            logger.error("")
            logger.error("OPCIONES:")
            logger.error("")
            logger.error("1. Ejecutar manualmente con psql como superusuario:")
            logger.error("   psql -U postgres -d nombre_base_datos -c 'CREATE EXTENSION IF NOT EXISTS pg_trgm;'")
            logger.error("")
            logger.error("2. O ejecutar el script SQL directamente:")
            logger.error("   psql -U postgres -d nombre_base_datos -f scripts/sql/instalar_extension_pg_trgm.sql")
            logger.error("")
            logger.error("3. Si estás en Render.com o similar, contacta al administrador")
            logger.error("   para que instale la extensión con permisos de superusuario.")
            logger.error("")
        else:
            logger.error(f"Error desconocido: {error_msg}")
        
        db.rollback()
        return False
    finally:
        db.close()

def main():
    """Función principal"""
    print("=" * 70)
    print("INSTALACIÓN DE EXTENSIÓN pg_trgm")
    print("=" * 70)
    print()
    
    # Verificar si ya está instalada
    estado = verificar_extension()
    
    if estado is True:
        print("OK: La extension pg_trgm ya esta instalada. No es necesario instalarla.")
        return 0
    
    if estado is None:
        print("ADVERTENCIA: No se pudo verificar el estado de la extension.")
        print()
    
    # Intentar instalar
    print("Intentando instalar extension pg_trgm...")
    print()
    
    if instalar_extension():
        print()
        print("=" * 70)
        print("OK: INSTALACION COMPLETADA")
        print("=" * 70)
        print()
        print("Ahora puedes ejecutar el script completo de indices:")
        print("  scripts/sql/indices_optimizacion_chat_ai.sql")
        print()
        return 0
    else:
        print()
        print("=" * 70)
        print("ERROR: INSTALACION FALLIDA")
        print("=" * 70)
        print()
        print("Consulta las instrucciones arriba para instalar manualmente.")
        print()
        return 1

if __name__ == "__main__":
    sys.exit(main())
