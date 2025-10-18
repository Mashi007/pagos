#!/usr/bin/env python3
"""
Script DEFINITIVO para corregir usuarios administradores
NO es temporal - es la solución permanente
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Obtener URL de la base de datos
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL no está configurada en las variables de entorno.")
    sys.exit(1)

# Crear motor de SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def fix_admin_users_definitive():
    """
    SOLUCIÓN DEFINITIVA: Corregir usuarios administradores
    NO es temporal - es la solución permanente
    """
    logger.info("🔧 SOLUCIÓN DEFINITIVA: Corrigiendo usuarios administradores...")
    db = SessionLocal()
    try:
        connection = db.connection()
        
        # Lista de usuarios que DEBEN ser administradores
        admin_emails = [
            'itmaster@rapicreditca.com',
            'admin@rapicredit.com',
            'admin@sistema.com',
            'daniel@rapicredit.com'
        ]
        
        logger.info("📋 Usuarios que serán marcados como administradores:")
        for email in admin_emails:
            logger.info(f"   - {email}")
        
        # Marcar usuarios específicos como administradores
        for email in admin_emails:
            result = connection.execute(text(f"""
                UPDATE usuarios 
                SET is_admin = TRUE, updated_at = NOW()
                WHERE email = '{email}' AND is_active = TRUE
            """))
            
            if result.rowcount > 0:
                logger.info(f"✅ Usuario {email} marcado como administrador")
            else:
                logger.warning(f"⚠️ Usuario {email} no encontrado o inactivo")
        
        # Verificar que al menos un usuario sea administrador
        admin_count = connection.execute(text("SELECT COUNT(*) FROM usuarios WHERE is_admin = TRUE")).scalar()
        
        if admin_count == 0:
            logger.error("🚨 CRÍTICO: No hay administradores en el sistema")
            logger.info("🔧 Creando usuario administrador por defecto...")
            
            # Crear usuario administrador por defecto
            connection.execute(text("""
                INSERT INTO usuarios (
                    email, nombre, apellido, hashed_password, 
                    is_admin, is_active, created_at
                ) VALUES (
                    'admin@rapicredit.com',
                    'Administrador',
                    'Sistema',
                    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4VqZ8K5K2C', -- admin123
                    TRUE,
                    TRUE,
                    NOW()
                )
                ON CONFLICT (email) DO UPDATE SET
                    is_admin = TRUE,
                    is_active = TRUE,
                    updated_at = NOW()
            """))
            logger.info("✅ Usuario administrador por defecto creado/actualizado")
        
        # Verificación final
        final_admin_count = connection.execute(text("SELECT COUNT(*) FROM usuarios WHERE is_admin = TRUE")).scalar()
        logger.info(f"✅ Total de administradores en el sistema: {final_admin_count}")
        
        # Mostrar lista de administradores
        admins = connection.execute(text("""
            SELECT email, nombre, apellido, is_active 
            FROM usuarios 
            WHERE is_admin = TRUE 
            ORDER BY email
        """)).fetchall()
        
        logger.info("📋 Lista de administradores:")
        for admin in admins:
            status = "ACTIVO" if admin.is_active else "INACTIVO"
            logger.info(f"   - {admin.email} ({admin.nombre} {admin.apellido}) - {status}")
        
        # Commit final
        db.commit()
        logger.info("🎉 SOLUCIÓN DEFINITIVA COMPLETADA")
        
    except Exception as e:
        logger.error(f"❌ Error durante la corrección: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fix_admin_users_definitive()
