# backend/app/api/v1/endpoints/users.py
"""
Endpoints de gestión de usuarios
CRUD completo (solo para ADMIN)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.api.deps import get_admin_user, get_current_user, get_pagination_params, PaginationParams
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.utils.auditoria_helper import (
    registrar_creacion, registrar_actualizacion, registrar_eliminacion, registrar_error
)
from app.core.security import get_password_hash
from app.utils.validators import validate_password_strength
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


router = APIRouter()


# ============================================
# VERIFICACIÓN DE ADMINISTRADORES
# ============================================

@router.get("/verificar-admin")
def verificar_rol_administracion(
    db: Session = Depends(get_db)
):
    """
    🔍 Verificar estado del rol de administración en el sistema
    """
    try:
        # Buscar todos los administradores
        admins = db.query(User).filter(User.is_admin == True).all()  # Cambio clave: rol → is_admin
        admins_activos = db.query(User).filter(
            User.is_admin == True,  # Cambio clave: rol → is_admin
            User.is_active == True
        ).all()
        
        # Estadísticas de usuarios por tipo
        tipos_stats = {
            "ADMIN": {
                "total": db.query(User).filter(User.is_admin == True).count(),
                "activos": db.query(User).filter(User.is_admin == True, User.is_active == True).count()
            },
            "USER": {
                "total": db.query(User).filter(User.is_admin == False).count(),
                "activos": db.query(User).filter(User.is_admin == False, User.is_active == True).count()
            }
        }
        
        # Estado del sistema
        sistema_funcional = len(admins_activos) > 0
        
        return {
            "titulo": "🔍 VERIFICACIÓN DEL ROL DE ADMINISTRACIÓN",
            "fecha_verificacion": datetime.now().isoformat(),
            
            "estado_administracion": {
                "activo": sistema_funcional,
                "total_admins": len(admins),
                "admins_activos": len(admins_activos),
                "estado": "✅ FUNCIONAL" if sistema_funcional else "❌ SIN ADMINISTRADOR ACTIVO"
            },
            
            "administradores_registrados": [
                {
                    "id": admin.id,
                    "email": admin.email,
                    "nombre_completo": admin.full_name,
                    "activo": admin.is_active,
                    "fecha_creacion": admin.created_at,
                    "ultimo_login": getattr(admin, 'last_login', None),
                    "estado": "✅ ACTIVO" if admin.is_active else "❌ INACTIVO"
                }
                for admin in admins
            ],
            
            "permisos_administrador": {
                "gestion_usuarios": "✅ Crear, editar, eliminar usuarios",
                "gestion_clientes": "✅ Acceso completo a todos los clientes",
                "gestion_pagos": "✅ Modificar, anular pagos sin aprobación",
                "reportes": "✅ Generar todos los reportes",
                "configuracion": "✅ Configurar parámetros del sistema",
                "aprobaciones": "✅ Aprobar/rechazar solicitudes",
                "carga_masiva": "✅ Realizar migraciones masivas",
                "auditoria": "✅ Ver logs completos del sistema",
                "dashboard": "✅ Dashboard administrativo completo"
            },
            
            "estadisticas_usuarios": {
                "por_tipo": tipos_stats,
                "total_usuarios": sum(stats["total"] for stats in tipos_stats.values()),
                "usuarios_activos": sum(stats["activos"] for stats in tipos_stats.values())
            },
            
            "recomendaciones": [
                "✅ Sistema funcional" if sistema_funcional else "❌ Crear usuario administrador",
                "🔐 Cambiar contraseñas por defecto" if any(admin.email == "itmaster@rapicreditca.com" for admin in admins) else None,
                "👥 Crear usuarios para otros roles según necesidades",
                "📊 Revisar dashboard administrativo regularmente",
                "🔔 Configurar notificaciones automáticas"
            ],
            
            "acciones_disponibles": {
                "crear_admin": "python backend/scripts/create_admin.py",
                "modo_interactivo": "python backend/scripts/create_admin.py --interactive",
                "listar_admins": "python backend/scripts/create_admin.py --list",
                "verificar_sistema": "python backend/scripts/create_admin.py --verify"
            },
            
            "urls_sistema": {
                "aplicacion": "https://pagos-f2qf.onrender.com",
                "documentacion": "https://pagos-f2qf.onrender.com/docs",
                "login": "POST /api/v1/auth/login",
                "dashboard_admin": "GET /api/v1/dashboard/admin",
                "verificar_admin": "GET /api/v1/users/verificar-admin"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verificando administración: {str(e)}")


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Crear usuario")
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Crear un nuevo usuario (solo ADMIN)
    
    - **email**: Email único del usuario
    - **nombre**: Nombre del usuario
    - **apellido**: Apellido del usuario
    - **cargo**: Cargo del usuario en la empresa (opcional)
    - **rol**: Rol del usuario (ADMIN, GERENTE, COBRANZAS, USER)
    - **password**: Contraseña (mínimo 8 caracteres)
    - **is_active**: Si el usuario está activo
    """
    # Verificar que el email no exista
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Validar fortaleza de contraseña
    is_valid, message = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Crear usuario
    new_user = User(
        email=user_data.email,
        nombre=user_data.nombre,
        apellido=user_data.apellido,
        cargo=user_data.cargo or "Usuario",  # Valor por defecto si es None
        is_admin=user_data.is_admin,  # Cambio clave: rol → is_admin
        hashed_password=get_password_hash(user_data.password),
        is_active=user_data.is_active,
        created_at=datetime.utcnow()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Registrar auditoría
    try:
        registrar_creacion(
            db=db,
            usuario=current_user,
            modulo="USUARIOS",
            tabla="usuarios",
            registro_id=new_user.id,
            descripcion=f"Usuario creado: {new_user.email} como {'Administrador' if new_user.is_admin else 'Usuario'}",
            datos_nuevos={
                "email": new_user.email,
                "nombre": new_user.nombre,
                "apellido": new_user.apellido,
                "is_admin": new_user.is_admin,  # Cambio clave: rol → is_admin
                "is_active": new_user.is_active
            }
        )
    except Exception as e:
        logger.warning(f"Error registrando auditoría de creación de usuario: {e}")
    
    return new_user


@router.get("/test-simple")
def test_users_simple(
    db: Session = Depends(get_db)
):
    """
    Test endpoint simple para verificar usuarios (sin autenticación)
    """
    try:
        total_users = db.query(User).count()
        users = db.query(User).limit(5).all()
        
        users_data = []
        for user in users:
            users_data.append({
                "id": user.id,
                "email": user.email,
                "nombre": user.nombre,
                "apellido": user.apellido,
                "is_admin": user.is_admin,  # Cambio clave: rol → is_admin
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None
            })
        
        return {
            "success": True,
            "total_users": total_users,
            "users": users_data,
            "message": "Test endpoint funcionando"
        }
    except Exception as e:
        logger.error(f"Error en test endpoint: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Error en test endpoint"
        }

@router.get("/test")
def test_users_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Test endpoint para verificar usuarios
    """
    try:
        total_users = db.query(User).count()
        users = db.query(User).limit(5).all()
        
        users_data = []
        for user in users:
            users_data.append({
                "id": user.id,
                "email": user.email,
                "nombre": user.nombre,
                "apellido": user.apellido,
                "is_admin": user.is_admin,  # Cambio clave: rol → is_admin
                "is_active": user.is_active
            })
        
        return {
            "status": "success",
            "total_users": total_users,
            "current_user": {
                "id": current_user.id,
                "email": current_user.email,
                "is_admin": current_user.is_admin  # Cambio clave: rol → is_admin
            },
            "users": users_data
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Error en test endpoint"
        }

@router.get("/")
def list_users(
    db: Session = Depends(get_db),
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_admin_user),
    is_active: bool = None
):
    """
    Listar usuarios con paginación (solo ADMIN)
    
    - **page**: Número de página (default: 1)
    - **page_size**: Tamaño de página (default: 10, max: 100)
    - **is_active**: Filtrar por estado activo/inactivo
    """
    query = db.query(User)
    
    # Filtros
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Total
    total = query.count()
    
    # Paginación
    users = query.offset(pagination.skip).limit(pagination.limit).all()
    
    return UserListResponse(
        items=users,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size
    )


@router.get("/{user_id}", response_model=UserResponse, summary="Obtener usuario")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Obtener un usuario por ID (solo ADMIN)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return user


@router.put("/{user_id}", response_model=UserResponse, summary="Actualizar usuario")
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Actualizar un usuario (solo ADMIN)
    
    Solo se actualizan los campos proporcionados
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Verificar email único si se está actualizando
    if user_data.email and user_data.email != user.email:
        existing = db.query(User).filter(User.email == user_data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya está registrado"
            )
    
    # Actualizar campos
    update_data = user_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_200_OK, summary="Eliminar usuario")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Eliminar un usuario (HARD DELETE - borrado completo de BD)
    
    Solo ADMIN puede eliminar usuarios permanentemente
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # No permitir eliminar el propio usuario
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propio usuario"
        )
    
    # HARD DELETE - eliminar completamente de la base de datos
    user_email = user.email  # Guardar email para log
    
    # Registrar auditoría antes de eliminar
    try:
        registrar_eliminacion(
            db=db,
            usuario=current_user,
            modulo="USUARIOS",
            tabla="usuarios",
            registro_id=user.id,
            descripcion=f"Usuario eliminado permanentemente: {user_email}",
            datos_anteriores={
                "email": user.email,
                "nombre": user.nombre,
                "apellido": user.apellido,
                "is_admin": user.is_admin,  # Cambio clave: rol → is_admin
                "is_active": user.is_active
            }
        )
    except Exception as e:
        logger.warning(f"Error registrando auditoría de eliminación de usuario: {e}")
    
    db.delete(user)
    db.commit()
    
    return {
        "message": f"Usuario {user_email} eliminado completamente de la base de datos"
    }


@router.post("/{user_id}/activate", response_model=UserResponse, summary="Activar usuario")
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Reactivar un usuario desactivado (solo ADMIN)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    user.is_active = True
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/{user_id}/deactivate", response_model=UserResponse, summary="Desactivar usuario")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    """
    Desactivar un usuario (solo ADMIN)
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    return user
