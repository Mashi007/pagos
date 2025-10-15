"""
Endpoint temporal para arreglar roles ADMIN en la base de datos
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/fix-admin-roles")
def fix_admin_roles(db: Session = Depends(get_db)):
    """
    🔧 Endpoint temporal para actualizar roles ADMIN a ADMINISTRADOR_GENERAL
    """
    try:
        # Verificar registros con rol ADMIN
        result = db.execute(text("SELECT id, email, rol FROM users WHERE rol = 'ADMIN'"))
        admin_users = result.fetchall()
        
        if admin_users:
            logger.info(f"🔍 Encontrados {len(admin_users)} usuarios con rol 'ADMIN'")
            
            # Actualizar roles ADMIN a ADMINISTRADOR_GENERAL
            update_result = db.execute(
                text("UPDATE users SET rol = 'ADMINISTRADOR_GENERAL' WHERE rol = 'ADMIN'")
            )
            db.commit()
            
            return {
                "message": f"✅ Actualizados {update_result.rowcount} registros de 'ADMIN' a 'ADMINISTRADOR_GENERAL'",
                "updated_count": update_result.rowcount,
                "users_updated": [{"id": user.id, "email": user.email} for user in admin_users],
                "status": "success"
            }
        else:
            return {
                "message": "✅ No se encontraron usuarios con rol 'ADMIN'",
                "updated_count": 0,
                "status": "no_changes_needed"
            }
            
    except Exception as e:
        logger.error(f"❌ Error actualizando roles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error actualizando roles: {str(e)}")

@router.get("/verify-roles")
def verify_roles(db: Session = Depends(get_db)):
    """
    📊 Verificar los roles actuales en la base de datos
    """
    try:
        result = db.execute(text("SELECT rol, COUNT(*) as count FROM users GROUP BY rol"))
        roles = result.fetchall()
        
        roles_data = [{"rol": role.rol, "count": role.count} for role in roles]
        
        return {
            "message": "📊 Roles actuales en la base de datos",
            "roles": roles_data,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"❌ Error verificando roles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error verificando roles: {str(e)}")

@router.get("/test-connection")
def test_connection():
    """
    🧪 Probar conexión básica sin base de datos
    """
    return {
        "message": "✅ Endpoint funcionando correctamente",
        "timestamp": "2025-10-15T15:20:00",
        "status": "ok"
    }
