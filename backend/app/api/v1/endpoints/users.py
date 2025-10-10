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
    - **rol**: Rol del usuario (ADMIN, ASESOR, COBRANZAS, CONTADOR)
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
