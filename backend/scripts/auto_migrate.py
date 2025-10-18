#!/usr/bin/env python3
"""
Script de migración automática para Render
Se ejecuta al iniciar el backend para asegurar que la migración se aplique
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_url():
    """Obtener URL de base de datos desde variables de entorno"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("❌ DATABASE_URL no encontrada en variables de entorno")
        return None
    return db_url

def check_column_exists(engine, table_name, column_name):
    """Verificar si una columna existe en la tabla"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = :table_name AND column_name = :column_name
            """), {"table_name": table_name, "column_name": column_name})
            
            return result.fetchone() is not None
    except Exception as e:
        logger.error(f"Error verificando columna: {e}")
        return False

def execute_migration_if_needed():
    """Ejecutar migración solo si es necesaria"""
    try:
        db_url = get_database_url()
        if not db_url:
            logger.error("❌ No se puede obtener URL de base de datos")
            return False
            
        logger.info("🔍 Verificando estado de migración...")
        engine = create_engine(db_url)
        
        # Verificar si is_admin existe
        if check_column_exists(engine, 'usuarios', 'is_admin'):
            logger.info("✅ Columna is_admin ya existe - migración no necesaria")
            return True
            
        # Verificar si rol existe
        if not check_column_exists(engine, 'usuarios', 'rol'):
            logger.error("❌ Ni is_admin ni rol existen - estructura de tabla inesperada")
            return False
            
        logger.info("🚀 Ejecutando migración de rol → is_admin...")
        
        with engine.connect() as conn:
            trans = conn.begin()
            
            try:
                # PASO 1: Agregar columna is_admin
                logger.info("➕ Agregando columna is_admin...")
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN is_admin BOOLEAN DEFAULT FALSE"))
                
                # PASO 2: Migrar datos
                logger.info("🔄 Migrando datos...")
                
                # Contar usuarios por rol
                result = conn.execute(text("SELECT rol, COUNT(*) FROM usuarios GROUP BY rol"))
                roles_count = result.fetchall()
                logger.info(f"Usuarios por rol: {dict(roles_count)}")
                
                # Migrar ADMIN → is_admin = TRUE
                result = conn.execute(text("UPDATE usuarios SET is_admin = TRUE WHERE rol = 'ADMIN'"))
                admin_count = result.rowcount
                logger.info(f"✅ Migrados {admin_count} usuarios ADMIN")
                
                # Migrar otros roles → is_admin = FALSE
                result = conn.execute(text("UPDATE usuarios SET is_admin = FALSE WHERE rol IN ('USER', 'GERENTE', 'COBRANZAS')"))
                other_count = result.rowcount
                logger.info(f"✅ Migrados {other_count} usuarios no-ADMIN")
                
                # PASO 3: Hacer is_admin NOT NULL
                logger.info("🔒 Haciendo is_admin NOT NULL...")
                conn.execute(text("ALTER TABLE usuarios ALTER COLUMN is_admin SET NOT NULL"))
                
                # PASO 4: Eliminar columna rol
                logger.info("🗑️ Eliminando columna rol...")
                conn.execute(text("ALTER TABLE usuarios DROP COLUMN rol"))
                
                # PASO 5: Eliminar tipo ENUM
                logger.info("🗑️ Eliminando tipo ENUM userrole...")
                conn.execute(text("DROP TYPE IF EXISTS userrole"))
                
                # PASO 6: Verificar resultado
                result = conn.execute(text("SELECT COUNT(*) FROM usuarios WHERE is_admin = TRUE"))
                admin_count = result.scalar()
                logger.info(f"✅ Total administradores: {admin_count}")
                
                if admin_count == 0:
                    logger.warning("⚠️ No hay administradores - creando uno por defecto")
                    conn.execute(text("UPDATE usuarios SET is_admin = TRUE WHERE id = 1"))
                
                trans.commit()
                logger.info("🎉 Migración completada exitosamente!")
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error durante migración: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Iniciando verificación de migración...")
    success = execute_migration_if_needed()
    
    if success:
        logger.info("✅ Verificación de migración completada")
        sys.exit(0)
    else:
        logger.error("❌ Error en verificación de migración")
        sys.exit(1)
