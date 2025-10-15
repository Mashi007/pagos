#!/usr/bin/env python3
"""
Script para actualizar roles ADMIN a ADMINISTRADOR_GENERAL en la base de datos
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_admin_roles():
    """Actualizar roles ADMIN a ADMINISTRADOR_GENERAL en la base de datos"""
    
    # URL de la base de datos desde variables de entorno
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL no encontrada en variables de entorno")
        return False
    
    try:
        # Crear conexión a la base de datos
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        
        with SessionLocal() as session:
            # Verificar registros con rol ADMIN
            result = session.execute(text("SELECT id, email, rol FROM users WHERE rol = 'ADMIN'"))
            admin_users = result.fetchall()
            
            if admin_users:
                logger.info(f"🔍 Encontrados {len(admin_users)} usuarios con rol 'ADMIN':")
                for user in admin_users:
                    logger.info(f"  - ID: {user.id}, Email: {user.email}")
                
                # Actualizar roles ADMIN a ADMINISTRADOR_GENERAL
                update_result = session.execute(
                    text("UPDATE users SET rol = 'ADMINISTRADOR_GENERAL' WHERE rol = 'ADMIN'")
                )
                session.commit()
                
                logger.info(f"✅ Actualizados {update_result.rowcount} registros de 'ADMIN' a 'ADMINISTRADOR_GENERAL'")
                
                # Verificar la actualización
                result = session.execute(text("SELECT COUNT(*) FROM users WHERE rol = 'ADMIN'"))
                remaining_admin = result.scalar()
                
                if remaining_admin == 0:
                    logger.info("✅ Todos los roles ADMIN han sido actualizados correctamente")
                    return True
                else:
                    logger.warning(f"⚠️  Aún quedan {remaining_admin} registros con rol ADMIN")
                    return False
            else:
                logger.info("✅ No se encontraron usuarios con rol 'ADMIN'")
                return True
                
    except Exception as e:
        logger.error(f"❌ Error actualizando roles: {str(e)}")
        return False

def verify_roles():
    """Verificar los roles actuales en la base de datos"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL no encontrada")
        return
    
    try:
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        
        with SessionLocal() as session:
            result = session.execute(text("SELECT rol, COUNT(*) as count FROM users GROUP BY rol"))
            roles = result.fetchall()
            
            logger.info("📊 Roles actuales en la base de datos:")
            for role in roles:
                logger.info(f"  - {role.rol}: {role.count} usuarios")
                
    except Exception as e:
        logger.error(f"❌ Error verificando roles: {str(e)}")

if __name__ == "__main__":
    logger.info("🔧 Iniciando actualización de roles ADMIN...")
    
    # Verificar roles actuales
    verify_roles()
    
    # Actualizar roles
    success = fix_admin_roles()
    
    if success:
        logger.info("🎉 Actualización completada exitosamente")
        verify_roles()
    else:
        logger.error("❌ La actualización falló")
        sys.exit(1)
