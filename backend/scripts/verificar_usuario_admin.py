#!/usr/bin/env python3
"""
Script para verificar el estado del usuario administrador
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL no está configurada...")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def verificar_usuario_admin():
    """Verificar el estado del usuario administrador"""
    logger.info("🔍 Verificando estado del usuario administrador...")
    
    db = SessionLocal()
    try:
        # Verificar estructura de la tabla usuarios
        logger.info("📋 Verificando estructura de tabla usuarios...")
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'usuarios' 
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        logger.info("Columnas de la tabla usuarios:")
        for col in columns:
            logger.info(f"  - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
        
        # Buscar usuarios administradores
        logger.info("👑 Buscando usuarios administradores...")
        result = db.execute(text("""
            SELECT id, email, nombre, apellido, is_admin, is_active, created_at, last_login
            FROM usuarios 
            WHERE is_admin = TRUE
            ORDER BY id
        """))
        
        admins = result.fetchall()
        
        if not admins:
            logger.warning("🚨 NO SE ENCONTRARON USUARIOS ADMINISTRADORES!")
            
            # Verificar si hay usuarios en general
            result = db.execute(text("SELECT COUNT(*) FROM usuarios"))
            total_users = result.scalar()
            logger.info(f"Total de usuarios en la base de datos: {total_users}")
            
            if total_users > 0:
                logger.info("📋 Todos los usuarios:")
                result = db.execute(text("""
                    SELECT id, email, nombre, apellido, is_admin, is_active
                    FROM usuarios 
                    ORDER BY id
                """))
                users = result.fetchall()
                for user in users:
                    logger.info(f"  - ID: {user[0]}, Email: {user[1]}, Nombre: {user[2]} {user[3]}, is_admin: {user[4]}, is_active: {user[5]}")
                
                # Crear un administrador
                logger.info("🔧 Creando usuario administrador...")
                db.execute(text("""
                    UPDATE usuarios 
                    SET is_admin = TRUE 
                    WHERE id = 1
                """))
                db.commit()
                logger.info("✅ Usuario con ID 1 marcado como administrador")
                
        else:
            logger.info(f"✅ Se encontraron {len(admins)} usuarios administradores:")
            for admin in admins:
                logger.info(f"  - ID: {admin[0]}, Email: {admin[1]}, Nombre: {admin[2]} {admin[3]}, is_admin: {admin[4]}, is_active: {admin[5]}")
                logger.info(f"    Creado: {admin[6]}, Último login: {admin[7]}")
        
        # Verificar usuario específico itmaster@rapicreditca.com
        logger.info("🔍 Verificando usuario específico: itmaster@rapicreditca.com...")
        result = db.execute(text("""
            SELECT id, email, nombre, apellido, is_admin, is_active, created_at, last_login
            FROM usuarios 
            WHERE email = 'itmaster@rapicreditca.com'
        """))
        
        user = result.fetchone()
        if user:
            logger.info(f"✅ Usuario encontrado:")
            logger.info(f"  - ID: {user[0]}")
            logger.info(f"  - Email: {user[1]}")
            logger.info(f"  - Nombre: {user[2]} {user[3]}")
            logger.info(f"  - is_admin: {user[4]}")
            logger.info(f"  - is_active: {user[5]}")
            logger.info(f"  - Creado: {user[6]}")
            logger.info(f"  - Último login: {user[7]}")
            
            if not user[4]:  # Si no es admin
                logger.warning("🚨 El usuario itmaster@rapicreditca.com NO es administrador!")
                logger.info("🔧 Marcando como administrador...")
                db.execute(text("""
                    UPDATE usuarios 
                    SET is_admin = TRUE 
                    WHERE email = 'itmaster@rapicreditca.com'
                """))
                db.commit()
                logger.info("✅ Usuario marcado como administrador")
            else:
                logger.info("✅ El usuario itmaster@rapicreditca.com ES administrador")
        else:
            logger.warning("🚨 Usuario itmaster@rapicreditca.com NO encontrado!")
        
        # Verificar permisos
        logger.info("🔐 Verificando sistema de permisos...")
        try:
            from app.core.permissions_simple import get_user_permissions, ADMIN_PERMISSIONS, USER_PERMISSIONS
            
            admin_perms = get_user_permissions(True)
            user_perms = get_user_permissions(False)
            
            logger.info(f"✅ Permisos de administrador ({len(admin_perms)}):")
            for perm in admin_perms:
                logger.info(f"  - {perm.value}")
            
            logger.info(f"✅ Permisos de usuario normal ({len(user_perms)}):")
            for perm in user_perms:
                logger.info(f"  - {perm.value}")
                
        except Exception as e:
            logger.error(f"❌ Error verificando permisos: {e}")
        
        logger.info("✅ Verificación completada exitosamente")
        
    except Exception as e:
        logger.error(f"❌ Error durante la verificación: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    verificar_usuario_admin()
