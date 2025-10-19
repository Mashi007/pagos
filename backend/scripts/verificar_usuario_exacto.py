# backend/scripts/verificar_usuario_exacto.py
"""
VERIFICACIÓN EXACTA DEL USUARIO - CUARTA AUDITORÍA
Verificar datos exactos del usuario itmaster@rapicreditca.com para confirmar causa raíz
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

def verificar_usuario_exacto():
    """
    Verificar datos exactos del usuario itmaster@rapicreditca.com
    """
    logger.info("🔍 VERIFICACIÓN EXACTA DEL USUARIO itmaster@rapicreditca.com")
    logger.info("=" * 80)
    logger.info(f"📅 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Confirmar datos exactos en base de datos")
    logger.info("=" * 80)
    
    # Conectar a base de datos
    db_url = get_database_url()
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 1. VERIFICACIÓN EXACTA DEL USUARIO ESPECÍFICO
        logger.info("👤 1. VERIFICACIÓN EXACTA DEL USUARIO")
        logger.info("-" * 50)
        
        result = db.execute(text("""
            SELECT 
                id, 
                email, 
                nombre, 
                apellido, 
                cargo,
                is_admin, 
                is_active, 
                created_at, 
                updated_at, 
                last_login,
                hashed_password IS NOT NULL as has_password
            FROM usuarios 
            WHERE email = 'itmaster@rapicreditca.com'
        """))
        
        user = result.fetchone()
        
        if not user:
            logger.error("❌ USUARIO NO ENCONTRADO")
            logger.error("🔍 CAUSA PROBABLE: Usuario no existe en base de datos")
            logger.error("💡 SOLUCIÓN: Crear usuario o verificar email")
            return False
        
        logger.info("✅ USUARIO ENCONTRADO - DATOS EXACTOS:")
        logger.info(f"   🆔 ID: {user[0]} ({type(user[0])})")
        logger.info(f"   📧 Email: {user[1]} ({type(user[1])})")
        logger.info(f"   👤 Nombre: {user[2]} ({type(user[2])})")
        logger.info(f"   👤 Apellido: {user[3]} ({type(user[3])})")
        logger.info(f"   💼 Cargo: {user[4]} ({type(user[4])})")
        logger.info(f"   🔑 is_admin: {user[5]} ({type(user[5])})")
        logger.info(f"   ✅ is_active: {user[6]} ({type(user[6])})")
        logger.info(f"   📅 Creado: {user[7]} ({type(user[7])})")
        logger.info(f"   🔄 Actualizado: {user[8]} ({type(user[8])})")
        logger.info(f"   🕐 Último login: {user[9]} ({type(user[9])})")
        logger.info(f"   🔐 Tiene password: {user[10]} ({type(user[10])})")
        
        # 2. ANÁLISIS CRÍTICO DE is_admin
        logger.info("\n🔑 2. ANÁLISIS CRÍTICO DE is_admin")
        logger.info("-" * 50)
        
        is_admin_value = user[5]
        is_admin_type = type(is_admin_value)
        
        logger.info(f"📊 Valor is_admin: {is_admin_value}")
        logger.info(f"📊 Tipo: {is_admin_type}")
        
        if is_admin_value is True:
            logger.info("✅ CONFIRMADO: Usuario ES administrador en BD")
            logger.info("🔍 CAUSA PROBABLE: Problema en frontend o caché")
        elif is_admin_value is False:
            logger.error("❌ PROBLEMA: Usuario NO es administrador en BD")
            logger.error("🔍 CAUSA CONFIRMADA: Datos incorrectos en base de datos")
            logger.error("💡 SOLUCIÓN: Actualizar is_admin a TRUE")
        elif is_admin_value is None:
            logger.error("❌ PROBLEMA: is_admin es NULL en BD")
            logger.error("🔍 CAUSA CONFIRMADA: Campo no inicializado")
            logger.error("💡 SOLUCIÓN: Establecer is_admin a TRUE")
        else:
            logger.error(f"❌ PROBLEMA: Valor is_admin inválido: {is_admin_value}")
            logger.error("🔍 CAUSA CONFIRMADA: Tipo de dato incorrecto")
            logger.error("💡 SOLUCIÓN: Corregir tipo de dato")
        
        # 3. VERIFICAR ESTADO DE ACTIVACIÓN
        logger.info("\n✅ 3. VERIFICAR ESTADO DE ACTIVACIÓN")
        logger.info("-" * 50)
        
        is_active_value = user[6]
        
        if is_active_value is True:
            logger.info("✅ Usuario está activo")
        elif is_active_value is False:
            logger.error("❌ PROBLEMA: Usuario está inactivo")
            logger.error("🔍 CAUSA: Usuario deshabilitado")
            logger.error("💡 SOLUCIÓN: Activar usuario")
        else:
            logger.error(f"❌ PROBLEMA: Estado de activación inválido: {is_active_value}")
        
        # 4. VERIFICAR OTROS USUARIOS ADMIN
        logger.info("\n👥 4. VERIFICAR OTROS USUARIOS ADMIN")
        logger.info("-" * 50)
        
        result = db.execute(text("""
            SELECT id, email, nombre, apellido, is_admin, is_active
            FROM usuarios 
            WHERE is_admin = TRUE
            ORDER BY id
        """))
        
        admins = result.fetchall()
        logger.info(f"📊 Total administradores en BD: {len(admins)}")
        
        for admin in admins:
            logger.info(f"   🔑 ID: {admin[0]}, Email: {admin[1]}, Admin: {admin[4]}, Activo: {admin[5]}")
        
        # 5. VERIFICAR ESTRUCTURA DE TABLA
        logger.info("\n📋 5. VERIFICAR ESTRUCTURA DE TABLA")
        logger.info("-" * 50)
        
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'usuarios' 
            AND column_name IN ('id', 'email', 'is_admin', 'is_active')
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        logger.info("📊 Columnas críticas:")
        for col in columns:
            logger.info(f"   - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
        
        # 6. CONCLUSIÓN FINAL
        logger.info("\n📊 CONCLUSIÓN FINAL")
        logger.info("=" * 80)
        
        if is_admin_value is True and is_active_value is True:
            logger.info("✅ DIAGNÓSTICO: Usuario ES administrador y está activo en BD")
            logger.info("🔍 CAUSA CONFIRMADA: Problema en frontend o caché")
            logger.info("💡 SOLUCIÓN: Verificar frontend y limpiar caché")
            logger.info("🎯 PRÓXIMO PASO: Auditar flujo frontend")
        else:
            logger.error("❌ DIAGNÓSTICO: Problema en base de datos")
            logger.error("🔍 CAUSA CONFIRMADA: Datos incorrectos en BD")
            logger.error("💡 SOLUCIÓN: Corregir datos en base de datos")
            logger.error("🎯 PRÓXIMO PASO: Actualizar datos en BD")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en verificación: {e}", exc_info=True)
        return False
    finally:
        db.close()

if __name__ == "__main__":
    verificar_usuario_exacto()
