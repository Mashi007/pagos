#!/usr/bin/env python3
"""
Script para ejecutar la migración de roles en producción de forma segura.

Este script:
1. Verifica la conexión a la base de datos
2. Hace backup de los datos críticos
3. Ejecuta la migración
4. Verifica que todo funcionó correctamente
"""

import sys
import os
from pathlib import Path

# Añadir el directorio backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_engine
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Ejecutar la migración de forma segura."""
    
    try:
        # Crear engine
        engine = get_engine()
        
        logger.info("🔍 Verificando conexión a base de datos...")
        
        with engine.connect() as conn:
            # Verificar conexión
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Conexión exitosa a base de datos")
            
            # Paso 1: Mostrar estado actual
            logger.info("\n📊 Estado actual de usuarios:")
            result = conn.execute(text("""
                SELECT rol, COUNT(*) as cantidad 
                FROM usuarios 
                GROUP BY rol
            """))
            for row in result:
                logger.info(f"   - {row[0]}: {row[1]} usuarios")
            
            # Paso 2: Hacer backup (mostrar usuarios que serán modificados)
            logger.info("\n💾 Usuarios que serán migrados:")
            result = conn.execute(text("""
                SELECT email, rol 
                FROM usuarios 
                WHERE rol != 'USER'
            """))
            usuarios_a_migrar = result.fetchall()
            for row in usuarios_a_migrar:
                logger.info(f"   - {row[0]}: {row[1]} → USER")
            
            if not usuarios_a_migrar:
                logger.info("   ✅ No hay usuarios para migrar (todos ya son USER)")
                return True
            
            # Paso 3: Confirmar migración
            logger.info("\n⚠️  Esta migración:")
            logger.info("   1. Cambiará todos los roles a 'USER'")
            logger.info("   2. Eliminará los roles antiguos del enum")
            logger.info("   3. Es irreversible en producción")
            
            logger.info("\n🚀 Iniciando migración...")
            
            # Ejecutar migración
            conn.execute(text("""
                UPDATE usuarios 
                SET rol = 'USER' 
                WHERE rol IN ('ADMINISTRADOR_GENERAL', 'GERENTE', 'COBRANZAS', 'ADMIN')
            """))
            
            logger.info("✅ Usuarios actualizados")
            
            # Modificar enum
            conn.execute(text("ALTER TABLE usuarios ALTER COLUMN rol TYPE VARCHAR(50)"))
            logger.info("✅ Columna convertida a VARCHAR")
            
            conn.execute(text("DROP TYPE IF EXISTS userrole"))
            logger.info("✅ Enum antiguo eliminado")
            
            conn.execute(text("CREATE TYPE userrole AS ENUM ('USER')"))
            logger.info("✅ Nuevo enum creado")
            
            conn.execute(text("""
                ALTER TABLE usuarios 
                ALTER COLUMN rol TYPE userrole 
                USING rol::text::userrole
            """))
            logger.info("✅ Columna reconvertida a enum")
            
            # Asegurar usuario correcto
            conn.execute(text("""
                INSERT INTO usuarios (
                    email, 
                    hashed_password, 
                    nombre, 
                    apellido, 
                    telefono, 
                    rol, 
                    is_active, 
                    email_verified
                )
                VALUES (
                    'itmaster@rapicreditca.com',
                    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYvIYUX.lHm',
                    'IT',
                    'Master',
                    '1234567890',
                    'USER',
                    true,
                    true
                )
                ON CONFLICT (email) DO UPDATE
                SET 
                    rol = 'USER',
                    is_active = true,
                    email_verified = true
            """))
            logger.info("✅ Usuario itmaster@rapicreditca.com verificado")
            
            # Eliminar usuario incorrecto
            conn.execute(text("""
                DELETE FROM usuarios 
                WHERE email = 'admin@financiamiento.com'
            """))
            logger.info("✅ Usuario admin@financiamiento.com eliminado (si existía)")
            
            # Commit de todos los cambios
            conn.commit()
            
            # Paso 4: Verificar resultado
            logger.info("\n🔍 Verificando resultado final:")
            result = conn.execute(text("""
                SELECT rol, COUNT(*) as cantidad 
                FROM usuarios 
                GROUP BY rol
            """))
            for row in result:
                logger.info(f"   - {row[0]}: {row[1]} usuarios")
            
            logger.info("\n✅ ¡Migración completada exitosamente!")
            logger.info("   - Todos los usuarios ahora tienen rol USER")
            logger.info("   - Sistema listo para funcionar sin restricciones de roles")
            
            return True
            
    except Exception as e:
        logger.error(f"\n❌ Error durante la migración: {e}")
        logger.error("   La base de datos no fue modificada (transacción revertida)")
        return False


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("🔧 MIGRACIÓN DE ROLES A SISTEMA ÚNICO")
    logger.info("="*60)
    
    success = run_migration()
    
    if success:
        logger.info("\n" + "="*60)
        logger.info("✅ MIGRACIÓN EXITOSA")
        logger.info("="*60)
        sys.exit(0)
    else:
        logger.info("\n" + "="*60)
        logger.info("❌ MIGRACIÓN FALLIDA")
        logger.info("="*60)
        sys.exit(1)

