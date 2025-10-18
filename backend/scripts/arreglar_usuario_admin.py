#!/usr/bin/env python3
"""
Script para arreglar el problema del usuario administrador
"""
import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL no está configurada...")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def arreglar_usuario_admin():
    """Arreglar el problema del usuario administrador"""
    logger.info("🔧 Arreglando problema del usuario administrador...")
    
    db = SessionLocal()
    try:
        # 1. Verificar si existe el usuario itmaster@rapicreditca.com
        logger.info("🔍 Verificando usuario itmaster@rapicreditca.com...")
        result = db.execute(text("""
            SELECT id, email, nombre, apellido, is_admin, is_active
            FROM usuarios 
            WHERE email = 'itmaster@rapicreditca.com'
        """))
        
        user = result.fetchone()
        
        if user:
            logger.info(f"✅ Usuario encontrado: ID {user[0]}, is_admin: {user[4]}, is_active: {user[5]}")
            
            # Si no es admin, marcarlo como admin
            if not user[4]:
                logger.info("🔧 Marcando usuario como administrador...")
                db.execute(text("""
                    UPDATE usuarios 
                    SET is_admin = TRUE 
                    WHERE email = 'itmaster@rapicreditca.com'
                """))
                db.commit()
                logger.info("✅ Usuario marcado como administrador")
            else:
                logger.info("✅ Usuario ya es administrador")
            
            # Asegurar que esté activo
            if not user[5]:
                logger.info("🔧 Activando usuario...")
                db.execute(text("""
                    UPDATE usuarios 
                    SET is_active = TRUE 
                    WHERE email = 'itmaster@rapicreditca.com'
                """))
                db.commit()
                logger.info("✅ Usuario activado")
            
        else:
            logger.warning("🚨 Usuario itmaster@rapicreditca.com NO encontrado!")
            
            # Verificar si hay otros usuarios
            result = db.execute(text("SELECT COUNT(*) FROM usuarios"))
            total_users = result.scalar()
            logger.info(f"Total de usuarios en la base de datos: {total_users}")
            
            if total_users > 0:
                # Mostrar todos los usuarios
                result = db.execute(text("""
                    SELECT id, email, nombre, apellido, is_admin, is_active
                    FROM usuarios 
                    ORDER BY id
                """))
                users = result.fetchall()
                
                logger.info("📋 Todos los usuarios:")
                for u in users:
                    logger.info(f"  - ID: {u[0]}, Email: {u[1]}, Nombre: {u[2]} {u[3]}, is_admin: {u[4]}, is_active: {u[5]}")
                
                # Marcar el primer usuario como admin
                logger.info("🔧 Marcando primer usuario como administrador...")
                db.execute(text("""
                    UPDATE usuarios 
                    SET is_admin = TRUE, is_active = TRUE 
                    WHERE id = 1
                """))
                db.commit()
                logger.info("✅ Primer usuario marcado como administrador")
        
        # 2. Verificar que haya al menos un admin
        logger.info("👑 Verificando administradores...")
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM usuarios 
            WHERE is_admin = TRUE AND is_active = TRUE
        """))
        
        admin_count = result.scalar()
        logger.info(f"Total de administradores activos: {admin_count}")
        
        if admin_count == 0:
            logger.error("🚨 NO HAY ADMINISTRADORES ACTIVOS!")
            return False
        else:
            logger.info("✅ Hay administradores activos")
        
        # 3. Verificar estructura de permisos
        logger.info("🔐 Verificando sistema de permisos...")
        try:
            # Importar funciones de permisos
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
            return False
        
        logger.info("✅ Problema del usuario administrador arreglado exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error durante el arreglo: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = arreglar_usuario_admin()
    if success:
        logger.info("🎉 Script completado exitosamente")
        sys.exit(0)
    else:
        logger.error("💥 Script falló")
        sys.exit(1)
