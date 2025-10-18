#!/usr/bin/env python3
"""
Script para ejecutar migración de rol → is_admin en producción
Equivale a ejecutar las migraciones 009_simplify_roles_to_boolean.py y 010_fix_roles_final.py
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
    # Variables de entorno comunes en Render
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        # Fallback a variables individuales
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'pagos')
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', '')
        
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    return db_url

def execute_migration():
    """Ejecutar migración de rol → is_admin"""
    try:
        # Conectar a la base de datos
        db_url = get_database_url()
        logger.info(f"Conectando a base de datos...")
        
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # Iniciar transacción
            trans = conn.begin()
            
            try:
                logger.info("🚀 Iniciando migración de rol → is_admin")
                
                # PASO 1: Verificar estructura actual
                logger.info("📋 Verificando estructura actual...")
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default 
                    FROM information_schema.columns 
                    WHERE table_name = 'usuarios' 
                    AND column_name IN ('rol', 'is_admin')
                    ORDER BY ordinal_position
                """))
                
                columns = result.fetchall()
                logger.info(f"Columnas encontradas: {[col[0] for col in columns]}")
                
                # PASO 2: Agregar columna is_admin
                logger.info("➕ Agregando columna is_admin...")
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE"))
                
                # PASO 3: Migrar datos
                logger.info("🔄 Migrando datos de rol → is_admin...")
                
                # Contar usuarios por rol actual
                result = conn.execute(text("SELECT rol, COUNT(*) FROM usuarios GROUP BY rol"))
                roles_count = result.fetchall()
                logger.info(f"Usuarios por rol actual: {dict(roles_count)}")
                
                # Migrar ADMIN → is_admin = TRUE
                result = conn.execute(text("UPDATE usuarios SET is_admin = TRUE WHERE rol = 'ADMIN'"))
                admin_count = result.rowcount
                logger.info(f"✅ Migrados {admin_count} usuarios ADMIN")
                
                # Migrar otros roles → is_admin = FALSE
                result = conn.execute(text("UPDATE usuarios SET is_admin = FALSE WHERE rol IN ('USER', 'GERENTE', 'COBRANZAS')"))
                other_count = result.rowcount
                logger.info(f"✅ Migrados {other_count} usuarios no-ADMIN")
                
                # PASO 4: Hacer is_admin NOT NULL
                logger.info("🔒 Haciendo is_admin NOT NULL...")
                conn.execute(text("ALTER TABLE usuarios ALTER COLUMN is_admin SET NOT NULL"))
                
                # PASO 5: Eliminar columna rol y tipo ENUM
                logger.info("🗑️ Eliminando columna rol...")
                conn.execute(text("ALTER TABLE usuarios DROP COLUMN IF EXISTS rol"))
                
                logger.info("🗑️ Eliminando tipo ENUM userrole...")
                conn.execute(text("DROP TYPE IF EXISTS userrole"))
                
                # PASO 6: Verificar resultado
                logger.info("✅ Verificando resultado...")
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default 
                    FROM information_schema.columns 
                    WHERE table_name = 'usuarios' 
                    AND column_name IN ('id', 'email', 'nombre', 'apellido', 'hashed_password', 'is_admin', 'cargo', 'is_active', 'created_at', 'updated_at', 'last_login')
                    ORDER BY ordinal_position
                """))
                
                final_columns = result.fetchall()
                logger.info(f"Columnas finales: {[col[0] for col in final_columns]}")
                
                # PASO 7: Verificar usuarios
                result = conn.execute(text("""
                    SELECT id, email, nombre, apellido, is_admin, is_active 
                    FROM usuarios 
                    ORDER BY id
                """))
                
                users = result.fetchall()
                logger.info(f"Usuarios migrados: {len(users)}")
                for user in users:
                    logger.info(f"  - {user[1]} ({user[2]} {user[3]}) - Admin: {user[4]}")
                
                # PASO 8: Verificar administradores
                result = conn.execute(text("SELECT COUNT(*) FROM usuarios WHERE is_admin = TRUE"))
                admin_count = result.scalar()
                logger.info(f"Total administradores: {admin_count}")
                
                if admin_count == 0:
                    logger.warning("⚠️ No hay administradores. Creando administrador por defecto...")
                    conn.execute(text("UPDATE usuarios SET is_admin = TRUE WHERE id = 1"))
                    logger.info("✅ Usuario con ID 1 marcado como administrador")
                
                # Confirmar transacción
                trans.commit()
                logger.info("🎉 Migración completada exitosamente!")
                
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error durante migración: {e}")
                raise
                
    except SQLAlchemyError as e:
        logger.error(f"❌ Error de base de datos: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    logger.info("🚀 Iniciando migración de roles...")
    execute_migration()
    logger.info("✅ Migración finalizada")
