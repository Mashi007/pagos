"""
Endpoint de emergencia para migrar roles en producción.

⚠️ USAR SOLO UNA VEZ Y ELIMINAR DESPUÉS ⚠️
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api import deps
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/emergency/migrate-roles")
async def emergency_migrate_roles(
    db: Session = Depends(deps.get_db)
):
    """
    🚨 ENDPOINT DE EMERGENCIA - MIGRACIÓN DE ROLES 🚨
    
    Este endpoint:
    1. Actualiza todos los usuarios al rol 'USER'
    2. Modifica el enum de PostgreSQL para solo tener 'USER'
    3. Elimina el usuario admin@financiamiento.com
    4. Verifica el usuario itmaster@rapicreditca.com
    
    ⚠️ IMPORTANTE:
    - Ejecutar solo UNA vez
    - No requiere autenticación por ser endpoint de emergencia
    - Eliminar este endpoint después de ejecutarlo
    """
    
    try:
        logger.info("🚨 INICIANDO MIGRACIÓN DE EMERGENCIA DE ROLES")
        
        # Paso 1: Verificar estado actual
        result = db.execute(text("""
            SELECT rol, COUNT(*) as cantidad 
            FROM usuarios 
            GROUP BY rol
        """))
        estado_inicial = {row[0]: row[1] for row in result}
        logger.info(f"📊 Estado inicial: {estado_inicial}")
        
        # Paso 2: Actualizar todos los usuarios a USER
        result = db.execute(text("""
            UPDATE usuarios 
            SET rol = 'USER' 
            WHERE rol IN ('ADMINISTRADOR_GENERAL', 'GERENTE', 'COBRANZAS', 'ADMIN')
            RETURNING email, rol
        """))
        usuarios_actualizados = result.fetchall()
        logger.info(f"✅ Actualizados {len(usuarios_actualizados)} usuarios")
        
        # Paso 3: Modificar el enum
        try:
            # Convertir columna a VARCHAR temporalmente
            db.execute(text("ALTER TABLE usuarios ALTER COLUMN rol TYPE VARCHAR(50)"))
            logger.info("✅ Columna convertida a VARCHAR")
            
            # Eliminar enum antiguo
            db.execute(text("DROP TYPE IF EXISTS userrole CASCADE"))
            logger.info("✅ Enum antiguo eliminado")
            
            # Crear nuevo enum solo con USER
            db.execute(text("CREATE TYPE userrole AS ENUM ('USER')"))
            logger.info("✅ Nuevo enum creado")
            
            # Reconvertir columna al enum
            db.execute(text("""
                ALTER TABLE usuarios 
                ALTER COLUMN rol TYPE userrole 
                USING rol::text::userrole
            """))
            logger.info("✅ Columna reconvertida a enum")
            
        except Exception as e:
            logger.error(f"❌ Error modificando enum: {e}")
            # Si falla la modificación del enum, al menos los usuarios están actualizados
            db.commit()
            return {
                "status": "partial_success",
                "message": "Usuarios actualizados pero enum no modificado",
                "error": str(e),
                "usuarios_actualizados": len(usuarios_actualizados),
                "estado_inicial": estado_inicial
            }
        
        # Paso 4: Asegurar usuario correcto
        db.execute(text("""
            INSERT INTO usuarios (
                email, 
                hashed_password, 
                nombre, 
                apellido, 
                telefono, 
                rol, 
                is_active, 
                email_verified,
                created_at,
                updated_at
            )
            VALUES (
                'itmaster@rapicreditca.com',
                '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYvIYUX.lHm',
                'IT',
                'Master',
                '1234567890',
                'USER',
                true,
                true,
                NOW(),
                NOW()
            )
            ON CONFLICT (email) DO UPDATE
            SET 
                rol = 'USER',
                is_active = true,
                email_verified = true,
                updated_at = NOW()
        """))
        logger.info("✅ Usuario itmaster@rapicreditca.com verificado")
        
        # Paso 5: Eliminar usuario incorrecto
        result = db.execute(text("""
            DELETE FROM usuarios 
            WHERE email = 'admin@financiamiento.com'
            RETURNING email
        """))
        eliminados = result.fetchall()
        if eliminados:
            logger.info(f"✅ Eliminado usuario admin@financiamiento.com")
        
        # Commit de todos los cambios
        db.commit()
        
        # Paso 6: Verificar estado final
        result = db.execute(text("""
            SELECT rol, COUNT(*) as cantidad 
            FROM usuarios 
            GROUP BY rol
        """))
        estado_final = {row[0]: row[1] for row in result}
        logger.info(f"📊 Estado final: {estado_final}")
        
        logger.info("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        
        return {
            "status": "success",
            "message": "Migración de roles completada exitosamente",
            "estado_inicial": estado_inicial,
            "estado_final": estado_final,
            "usuarios_actualizados": len(usuarios_actualizados),
            "usuarios_eliminados": len(eliminados),
            "acciones": [
                "✅ Todos los usuarios migrados a rol USER",
                "✅ Enum actualizado a solo USER",
                "✅ Usuario itmaster@rapicreditca.com verificado",
                "✅ Usuario admin@financiamiento.com eliminado" if eliminados else "ℹ️ Usuario admin@financiamiento.com no existía"
            ],
            "siguiente_paso": "⚠️ ELIMINAR este endpoint del código y hacer redeploy"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error en migración: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Error durante la migración",
                "message": str(e),
                "solution": "Verificar logs y estado de la base de datos"
            }
        )


@router.get("/emergency/check-roles")
async def check_roles_status(
    db: Session = Depends(deps.get_db)
):
    """
    Verificar el estado actual de los roles en la base de datos.
    No requiere autenticación.
    """
    
    try:
        # Obtener distribución de roles
        result = db.execute(text("""
            SELECT rol, COUNT(*) as cantidad 
            FROM usuarios 
            GROUP BY rol
        """))
        distribucion_roles = {row[0]: row[1] for row in result}
        
        # Verificar enum actual
        result = db.execute(text("""
            SELECT e.enumlabel 
            FROM pg_type t 
            JOIN pg_enum e ON t.oid = e.enumtypid  
            WHERE t.typname = 'userrole'
            ORDER BY e.enumsortorder
        """))
        enum_valores = [row[0] for row in result]
        
        # Verificar usuarios clave
        result = db.execute(text("""
            SELECT email, rol, is_active, email_verified
            FROM usuarios
            WHERE email IN ('itmaster@rapicreditca.com', 'admin@financiamiento.com')
        """))
        usuarios_clave = [
            {
                "email": row[0],
                "rol": row[1],
                "is_active": row[2],
                "email_verified": row[3]
            }
            for row in result
        ]
        
        # Determinar si necesita migración
        necesita_migracion = (
            len(enum_valores) > 1 or 
            'USER' not in enum_valores or
            any(rol != 'USER' for rol in distribucion_roles.keys())
        )
        
        return {
            "necesita_migracion": necesita_migracion,
            "distribucion_roles": distribucion_roles,
            "enum_valores": enum_valores,
            "usuarios_clave": usuarios_clave,
            "total_usuarios": sum(distribucion_roles.values()),
            "mensaje": "⚠️ Ejecutar /emergency/migrate-roles" if necesita_migracion else "✅ Sistema correcto"
        }
        
    except Exception as e:
        logger.error(f"❌ Error verificando roles: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Error verificando estado de roles",
                "message": str(e)
            }
        )

