"""
Endpoint de emergencia para arreglar roles sin depender de ORM
"""
from fastapi import APIRouter, HTTPException
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/fix-roles-direct")
def fix_roles_direct():
    """
    🚨 Corrección directa de roles usando psycopg2 (sin ORM)
    """
    try:
        # Obtener URL de la base de datos
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL no encontrada")
        
        # Conectar directamente con psycopg2
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verificar usuarios con rol ADMIN
        cursor.execute("SELECT id, email, rol FROM users WHERE rol = 'ADMIN'")
        admin_users = cursor.fetchall()
        
        if admin_users:
            logger.info(f"🔍 Encontrados {len(admin_users)} usuarios con rol ADMIN")
            
            # Actualizar roles ADMIN a ADMINISTRADOR_GENERAL
            cursor.execute("UPDATE users SET rol = 'ADMINISTRADOR_GENERAL' WHERE rol = 'ADMIN'")
            updated_count = cursor.rowcount
            
            # Confirmar cambios
            conn.commit()
            
            # Verificar actualización
            cursor.execute("SELECT COUNT(*) as count FROM users WHERE rol = 'ADMIN'")
            remaining_admin = cursor.fetchone()['count']
            
            cursor.close()
            conn.close()
            
            return {
                "message": f"✅ Actualizados {updated_count} usuarios de ADMIN a ADMINISTRADOR_GENERAL",
                "updated_count": updated_count,
                "remaining_admin": remaining_admin,
                "users_updated": [{"id": user['id'], "email": user['email']} for user in admin_users],
                "status": "success"
            }
        else:
            cursor.close()
            conn.close()
            return {
                "message": "✅ No se encontraron usuarios con rol ADMIN",
                "updated_count": 0,
                "status": "no_changes_needed"
            }
            
    except Exception as e:
        logger.error(f"❌ Error en corrección directa: {str(e)}")
        return {
            "message": f"❌ Error: {str(e)}",
            "status": "error"
        }

@router.get("/verify-roles-direct")
def verify_roles_direct():
    """
    📊 Verificar roles usando conexión directa
    """
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL no encontrada")
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT rol, COUNT(*) as count FROM users GROUP BY rol")
        roles = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            "message": "📊 Roles actuales en la base de datos",
            "roles": [{"rol": role['rol'], "count": role['count']} for role in roles],
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"❌ Error verificando roles: {str(e)}")
        return {
            "message": f"❌ Error: {str(e)}",
            "status": "error"
        }

@router.get("/health")
def health_check():
    """
    🏥 Check de salud básico
    """
    return {
        "message": "✅ Endpoint de emergencia funcionando",
        "timestamp": "2025-10-15T15:30:00",
        "status": "healthy"
    }
