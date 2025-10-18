# backend/scripts/diagnostico_tiempo_real.py
"""
DIAGNÓSTICO EN TIEMPO REAL - TERCERA AUDITORÍA
Verificar datos exactos en producción para confirmar la causa raíz
"""
import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_url():
    """Obtener URL de base de datos desde variables de entorno"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("❌ DATABASE_URL no encontrada en variables de entorno")
        sys.exit(1)
    return db_url

def diagnostico_tiempo_real():
    """
    DIAGNÓSTICO COMPLETO EN TIEMPO REAL
    """
    logger.info("🔍 INICIANDO DIAGNÓSTICO EN TIEMPO REAL")
    logger.info("=" * 60)
    
    # Conectar a base de datos
    db_url = get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 1. VERIFICAR ESTRUCTURA DE TABLA USUARIOS
        logger.info("📋 1. VERIFICANDO ESTRUCTURA DE TABLA USUARIOS")
        logger.info("-" * 40)
        
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'usuarios' 
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        logger.info(f"✅ Columnas encontradas: {len(columns)}")
        for col in columns:
            logger.info(f"   - {col[0]}: {col[1]} (nullable: {col[2]})")
        
        # 2. VERIFICAR USUARIO ESPECÍFICO itmaster@rapicreditca.com
        logger.info("\n🔍 2. VERIFICANDO USUARIO ESPECÍFICO")
        logger.info("-" * 40)
        
        result = db.execute(text("""
            SELECT id, email, nombre, apellido, is_admin, is_active, 
                   created_at, updated_at, last_login, cargo
            FROM usuarios 
            WHERE email = 'itmaster@rapicreditca.com'
        """))
        
        user = result.fetchone()
        if user:
            logger.info("✅ USUARIO ENCONTRADO:")
            logger.info(f"   📧 Email: {user[1]}")
            logger.info(f"   🆔 ID: {user[0]}")
            logger.info(f"   👤 Nombre: {user[2]} {user[3]}")
            logger.info(f"   🔑 is_admin: {user[4]} ({type(user[4])})")
            logger.info(f"   ✅ is_active: {user[5]} ({type(user[5])})")
            logger.info(f"   💼 Cargo: {user[9]}")
            logger.info(f"   📅 Creado: {user[6]}")
            logger.info(f"   🔄 Actualizado: {user[7]}")
            logger.info(f"   🕐 Último login: {user[8]}")
            
            # Verificar si es realmente admin
            if user[4] is True:
                logger.info("✅ CONFIRMADO: Usuario ES administrador en BD")
            elif user[4] is False:
                logger.error("❌ PROBLEMA: Usuario NO es administrador en BD")
            else:
                logger.error(f"❌ PROBLEMA: Valor is_admin inválido: {user[4]} ({type(user[4])})")
        else:
            logger.error("❌ USUARIO NO ENCONTRADO en base de datos")
            return False
        
        # 3. VERIFICAR TODOS LOS USUARIOS ADMIN
        logger.info("\n👥 3. VERIFICANDO TODOS LOS USUARIOS ADMIN")
        logger.info("-" * 40)
        
        result = db.execute(text("""
            SELECT id, email, nombre, apellido, is_admin, is_active
            FROM usuarios 
            WHERE is_admin = TRUE
            ORDER BY id
        """))
        
        admins = result.fetchall()
        logger.info(f"📊 Total administradores: {len(admins)}")
        
        for admin in admins:
            logger.info(f"   🔑 {admin[1]} - {admin[2]} {admin[3]} (ID: {admin[0]})")
        
        # 4. VERIFICAR PERMISOS DEL SISTEMA
        logger.info("\n🔐 4. VERIFICANDO SISTEMA DE PERMISOS")
        logger.info("-" * 40)
        
        try:
            # Importar módulo de permisos
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            from app.core.permissions_simple import ADMIN_PERMISSIONS, get_user_permissions
            
            logger.info(f"📋 Permisos definidos para ADMIN: {len(ADMIN_PERMISSIONS)}")
            
            # Simular permisos para usuario admin
            permissions = get_user_permissions(True)  # True = is_admin
            logger.info(f"✅ Permisos obtenidos para admin: {len(permissions)}")
            
            # Verificar permisos críticos
            critical_permissions = [
                "user:create", "user:read", "user:update", "user:delete",
                "cliente:create", "cliente:read", "cliente:update", "cliente:delete",
                "prestamo:create", "prestamo:read", "prestamo:update", "prestamo:delete",
                "dashboard:view", "audit:read"
            ]
            
            missing_permissions = []
            for perm in critical_permissions:
                if perm not in [p.value for p in permissions]:
                    missing_permissions.append(perm)
            
            if missing_permissions:
                logger.error(f"❌ Permisos críticos faltantes: {missing_permissions}")
            else:
                logger.info("✅ Todos los permisos críticos están presentes")
                
        except Exception as e:
            logger.error(f"❌ Error verificando permisos: {e}")
        
        # 5. VERIFICAR TOKENS JWT (si es posible)
        logger.info("\n🎫 5. VERIFICANDO CONFIGURACIÓN JWT")
        logger.info("-" * 40)
        
        try:
            from app.core.config import get_settings
            settings = get_settings()
            
            logger.info(f"🔑 SECRET_KEY configurada: {bool(settings.SECRET_KEY)}")
            logger.info(f"⏰ ACCESS_TOKEN_EXPIRE_MINUTES: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}")
            logger.info(f"🔄 REFRESH_TOKEN_EXPIRE_DAYS: {settings.REFRESH_TOKEN_EXPIRE_DAYS}")
            logger.info(f"🔐 ALGORITHM: {settings.ALGORITHM}")
            
        except Exception as e:
            logger.error(f"❌ Error verificando configuración JWT: {e}")
        
        # 6. RESUMEN FINAL
        logger.info("\n📊 RESUMEN FINAL")
        logger.info("=" * 60)
        
        if user and user[4] is True:
            logger.info("✅ DIAGNÓSTICO: Usuario ES administrador en base de datos")
            logger.info("🔍 CAUSA PROBABLE: Problema en frontend o caché")
            logger.info("💡 SOLUCIÓN: Verificar datos en frontend y limpiar caché")
        else:
            logger.error("❌ DIAGNÓSTICO: Usuario NO es administrador en base de datos")
            logger.error("🔍 CAUSA PROBABLE: Problema en base de datos")
            logger.error("💡 SOLUCIÓN: Actualizar is_admin en base de datos")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en diagnóstico: {e}", exc_info=True)
        return False
    finally:
        db.close()

if __name__ == "__main__":
    diagnostico_tiempo_real()
