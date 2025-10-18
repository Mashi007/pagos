# backend/app/api/v1/endpoints/verificar_permisos.py
"""
Endpoint para verificar que el usuario admin tenga TODOS los permisos necesarios
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.permissions_simple import get_user_permissions, ADMIN_PERMISSIONS, Permission

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/verificar-permisos-completos")
def verificar_permisos_completos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verificar que el usuario admin tenga TODOS los permisos necesarios
    """
    try:
        logger.info(f"Verificando permisos completos para usuario: {current_user.email}")
        
        # Obtener permisos del usuario
        user_permissions = get_user_permissions(current_user.is_admin)
        
        # Permisos críticos que debe tener un admin
        permisos_criticos = [
            Permission.VIEW_DASHBOARD,
            Permission.USER_CREATE,
            Permission.USER_READ,
            Permission.USER_UPDATE,
            Permission.USER_DELETE,
            Permission.CLIENTE_CREATE,
            Permission.CLIENTE_READ,
            Permission.CLIENTE_UPDATE,
            Permission.CLIENTE_DELETE,
            Permission.PRESTAMO_CREATE,
            Permission.PRESTAMO_READ,
            Permission.PRESTAMO_UPDATE,
            Permission.PRESTAMO_DELETE,
            Permission.PRESTAMO_APPROVE,
            Permission.PAGO_CREATE,
            Permission.PAGO_READ,
            Permission.PAGO_UPDATE,
            Permission.PAGO_DELETE,
            Permission.ANALISTA_CREATE,
            Permission.ANALISTA_READ,
            Permission.ANALISTA_UPDATE,
            Permission.ANALISTA_DELETE,
            Permission.CONCESIONARIO_CREATE,
            Permission.CONCESIONARIO_READ,
            Permission.CONCESIONARIO_UPDATE,
            Permission.CONCESIONARIO_DELETE,
            Permission.MODELO_CREATE,
            Permission.MODELO_READ,
            Permission.MODELO_UPDATE,
            Permission.MODELO_DELETE,
            Permission.REPORTE_READ,
            Permission.AUDIT_READ,
            Permission.CONFIG_READ,
            Permission.CONFIG_UPDATE,
            Permission.CONFIG_MANAGE,
        ]
        
        # Verificar permisos faltantes
        permisos_faltantes = []
        permisos_presentes = []
        
        for permiso in permisos_criticos:
            if permiso in user_permissions:
                permisos_presentes.append(permiso.value)
            else:
                permisos_faltantes.append(permiso.value)
        
        # Verificar si es admin
        es_admin = current_user.is_admin
        
        # Resultado
        resultado = {
            "usuario": {
                "email": current_user.email,
                "nombre": f"{current_user.nombre} {current_user.apellido}",
                "is_admin": es_admin,
                "is_active": current_user.is_active
            },
            "permisos": {
                "total_permisos": len(user_permissions),
                "permisos_criticos_requeridos": len(permisos_criticos),
                "permisos_presentes": len(permisos_presentes),
                "permisos_faltantes": len(permisos_faltantes),
                "lista_permisos_presentes": permisos_presentes,
                "lista_permisos_faltantes": permisos_faltantes
            },
            "estado": {
                "tiene_todos_los_permisos": len(permisos_faltantes) == 0,
                "es_admin": es_admin,
                "puede_acceder_todas_las_funciones": es_admin and len(permisos_faltantes) == 0
            }
        }
        
        logger.info(f"Verificación completada - Permisos presentes: {len(permisos_presentes)}, Faltantes: {len(permisos_faltantes)}")
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error verificando permisos: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verificando permisos: {str(e)}"
        )

@router.get("/listar-todos-permisos")
def listar_todos_los_permisos(
    current_user: User = Depends(get_current_user)
):
    """
    Listar todos los permisos disponibles en el sistema
    """
    try:
        logger.info(f"Listando todos los permisos para usuario: {current_user.email}")
        
        # Obtener permisos del usuario
        user_permissions = get_user_permissions(current_user.is_admin)
        
        # Todos los permisos del sistema
        todos_los_permisos = [perm.value for perm in Permission]
        
        return {
            "usuario": {
                "email": current_user.email,
                "is_admin": current_user.is_admin
            },
            "permisos_sistema": {
                "total_permisos_disponibles": len(todos_los_permisos),
                "lista_completa": todos_los_permisos
            },
            "permisos_usuario": {
                "total_permisos_usuario": len(user_permissions),
                "lista_permisos_usuario": [perm.value for perm in user_permissions]
            },
            "comparacion": {
                "tiene_todos_los_permisos": len(user_permissions) == len(todos_los_permisos),
                "permisos_faltantes": len(todos_los_permisos) - len(user_permissions)
            }
        }
        
    except Exception as e:
        logger.error(f"Error listando permisos: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listando permisos: {str(e)}"
        )
