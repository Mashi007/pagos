# backend/app/api/v1/endpoints/users.py
"""
Endpoints de gestión de usuarios
CRUD completo (solo para ADMIN)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.api.deps import get_admin_user, get_pagination_params, PaginationParams
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.core.security import get_password_hash, validate_password_strength
from datetime import datetime


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
        admins = db.query(User).filter(User.rol == "ADMINISTRADOR_GENERAL").all()
        admins_activos = db.query(User).filter(
            User.rol == "ADMINISTRADOR_GENERAL",
            User.is_active == True
        ).all()
        
        # Estadísticas de usuarios por rol
        roles_stats = {}
        for rol in ["ADMINISTRADOR_GENERAL", "GERENTE", "COBRANZAS"]:
            count = db.query(User).filter(User.rol == rol).count()
            activos = db.query(User).filter(User.rol == rol, User.is_active == True).count()
            roles_stats[rol] = {"total": count, "activos": activos}
        
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
                "por_rol": roles_stats,
                "total_usuarios": sum(stats["total"] for stats in roles_stats.values()),
                "usuarios_activos": sum(stats["activos"] for stats in roles_stats.values())
            },
            
            "recomendaciones": [
                "✅ Sistema funcional" if sistema_funcional else "❌ Crear usuario administrador",
                "🔐 Cambiar contraseñas por defecto" if any(admin.email == "admin@financiamiento.com" for admin in admins) else None,
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
    - **rol**: Rol del usuario (ADMINISTRADOR_GENERAL, GERENTE, COBRANZAS)
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
        rol=user_data.rol.value,
        hashed_password=get_password_hash(user_data.password),
        is_active=user_data.is_active,
        created_at=datetime.utcnow()
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.get("/", response_model=UserListResponse, summary="Listar usuarios")
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
        users=users,
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
        if field == "rol":
            setattr(user, field, value.value if value else None)
        else:
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
    Desactivar un usuario (soft delete - solo ADMIN)
    
    No se eliminan usuarios de la base de datos, solo se marcan como inactivos
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
    
    # Soft delete
    user.is_active = False
    user.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": f"Usuario {user.email} desactivado exitosamente"
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
