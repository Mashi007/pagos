#!/usr/bin/env python3
"""
Script para corregir el estado de administrador del usuario itmaster@rapicreditca.com
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

def fix_admin_user():
    logger.info("🔧 Iniciando corrección del usuario administrador...")
    db = SessionLocal()
    try:
        # Verificar estado actual del usuario
        result = db.execute(text("""
            SELECT id, email, nombre, apellido, is_admin, is_active 
            FROM usuarios 
            WHERE email = 'itmaster@rapicreditca.com'
        """)).fetchone()
        
        if not result:
            logger.error("❌ Usuario itmaster@rapicreditca.com no encontrado")
            return
        
        user_id, email, nombre, apellido, is_admin, is_active = result
        logger.info(f"📋 Usuario encontrado: {email}")
        logger.info(f"   - ID: {user_id}")
        logger.info(f"   - Nombre: {nombre} {apellido}")
        logger.info(f"   - is_admin: {is_admin}")
        logger.info(f"   - is_active: {is_active}")
        
        if is_admin:
            logger.info("✅ El usuario ya es administrador")
            return
        
        # Corregir el estado de administrador
        logger.info("🔧 Marcando usuario como administrador...")
        db.execute(text("""
            UPDATE usuarios 
            SET is_admin = TRUE, updated_at = NOW()
            WHERE email = 'itmaster@rapicreditca.com'
        """))
        db.commit()
        
        # Verificar el cambio
        result = db.execute(text("""
            SELECT is_admin 
            FROM usuarios 
            WHERE email = 'itmaster@rapicreditca.com'
        """)).fetchone()
        
        if result and result[0]:
            logger.info("✅ Usuario marcado como administrador exitosamente")
        else:
            logger.error("❌ Error al marcar usuario como administrador")
            
    except Exception as e:
        logger.error(f"❌ Error durante la corrección: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fix_admin_user()
