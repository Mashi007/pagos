"""
Endpoint para ejecutar SQL directo sin ORM
"""
from fastapi import APIRouter
import os
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/fix-enum")
def fix_enum_first():
    """
    🔧 Actualizar enum para incluir ADMINISTRADOR_GENERAL
    """
    try:
        import psycopg2
        
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return {"error": "DATABASE_URL no encontrada", "status": "error"}
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Agregar ADMINISTRADOR_GENERAL al enum si no existe
        cursor.execute("ALTER TYPE user_role_enum ADD VALUE IF NOT EXISTS 'ADMINISTRADOR_GENERAL'")
        conn.commit()
        
        cursor.close()
        conn.close()
        
        return {
            "message": "✅ Enum actualizado: agregado ADMINISTRADOR_GENERAL",
            "status": "success"
        }
        
    except Exception as e:
        return {
            "message": f"❌ Error actualizando enum: {str(e)}",
            "status": "error"
        }

@router.get("/fix-now")
def fix_roles_now():
    """
    🚨 Ejecutar corrección de roles inmediatamente
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # URL de la base de datos
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return {"error": "DATABASE_URL no encontrada", "status": "error"}
        
        # Conectar y ejecutar
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verificar usuarios ADMIN
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE rol = 'ADMIN'")
        admin_count = cursor.fetchone()['count']
        
        if admin_count > 0:
            # Primero verificar si el valor ya existe en el enum
            cursor.execute("SELECT EXISTS (SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid WHERE t.typname = 'user_role_enum' AND e.enumlabel = 'ADMINISTRADOR_GENERAL')")
            enum_exists = cursor.fetchone()[0]
            
            if not enum_exists:
                # Agregar el nuevo valor al enum si no existe
                cursor.execute("ALTER TYPE user_role_enum ADD VALUE 'ADMINISTRADOR_GENERAL'")
                conn.commit()
            
            # Luego actualizar roles
            cursor.execute("UPDATE users SET rol = 'ADMINISTRADOR_GENERAL' WHERE rol = 'ADMIN'")
            updated = cursor.rowcount
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return {
                "message": f"✅ ÉXITO: Actualizados {updated} usuarios de ADMIN a ADMINISTRADOR_GENERAL",
                "admin_found": admin_count,
                "updated": updated,
                "status": "success"
            }
        else:
            cursor.close()
            conn.close()
            return {
                "message": "✅ No hay usuarios con rol ADMIN",
                "admin_found": 0,
                "status": "no_changes"
            }
            
    except Exception as e:
        return {
            "message": f"❌ Error: {str(e)}",
            "status": "error"
        }

@router.get("/status")
def check_status():
    """
    📊 Verificar estado de roles
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return {"error": "DATABASE_URL no encontrada"}
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT rol, COUNT(*) as count FROM users GROUP BY rol ORDER BY count DESC")
        roles = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "message": "📊 Estado actual de roles",
            "roles": [{"rol": r['rol'], "count": r['count']} for r in roles],
            "status": "success"
        }
        
    except Exception as e:
        return {
            "message": f"❌ Error: {str(e)}",
            "status": "error"
        }

@router.get("/ping")
def ping():
    """
    🏓 Ping simple
    """
    return {"message": "pong", "status": "ok", "version": "1e605ea", "update": "enum_fix_compatible"}
