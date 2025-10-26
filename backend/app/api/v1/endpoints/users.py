import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserUpdate
from app.utils.validators import validate_password_strength

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/verificar-admin")
def verificar_rol_administracion(db: Session = Depends(get_db)):
    # Verificar estado del rol de administración en el sistema
    try:
        admin = db.query(User).filter(User.is_admin).first()

        if not admin:
            return {
                "tiene_admin": False,
                "mensaje": "No hay administradores en el sistema",
            }

        return {
            "tiene_admin": True,
            "admin_info": {
                "id": admin.id,
                "email": admin.email,
                "nombre": admin.nombre,
                "apellido": admin.apellido,
                "activo": admin.is_active,
                "fecha_creacion": admin.created_at,
                "ultimo_login": getattr(admin, "last_login", None),
            },
            "mensaje": "Sistema tiene administrador",
        }

    except Exception as e:
        logger.error(f"Error verificando administrador: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Crear un nuevo usuario (solo ADMIN)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="Solo administradores pueden crear usuarios"
        )
    # - email: Email único del usuario
    # - nombre: Nombre del usuario
    # - apellido: Apellido del usuario
    # - cargo: Cargo del usuario en la empresa (opcional)
    # - rol: Rol del usuario (ADMIN/USER)
    # - password: Contraseña (mínimo 8 caracteres)
    # - is_active: Si el usuario está activo

    # Verificar que el email no exista
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado",
        )

    # Validar fortaleza de contraseña
    is_valid, message = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    # Crear usuario
    new_user = User(
        email=user_data.email,
        nombre=user_data.nombre,
        apellido=user_data.apellido,
        rol="ADMIN" if user_data.is_admin else "USER",
        cargo=user_data.cargo,
        is_admin=user_data.is_admin,
        hashed_password=get_password_hash(user_data.password),
        is_active=user_data.is_active,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/", response_model=UserListResponse)
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Listar usuarios con paginación
    try:
        # Solo admins pueden ver todos los usuarios
        if not current_user.is_admin:
            raise HTTPException(
                status_code=403, detail="Solo administradores pueden listar usuarios"
            )

        users = db.query(User).offset(skip).limit(limit).all()
        total = db.query(User).count()

        return UserListResponse(
            items=users, total=total, page=skip // limit + 1, page_size=limit
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando usuarios: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Obtener usuario específico
    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Solo admins pueden ver otros usuarios, o el usuario puede verse a sí mismo
        if not current_user.is_admin and current_user.id != user_id:
            raise HTTPException(
                status_code=403, detail="No tienes permisos para ver este usuario"
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo usuario: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Actualizar usuario
    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Solo admins pueden actualizar otros usuarios, o el usuario puede actualizarse a sí mismo
        if not current_user.is_admin and current_user.id != user_id:
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para actualizar este usuario",
            )

        # Actualizar campos
        for field, value in user_data.model_dump(exclude_unset=True).items():
            if field == "password" and value:
                # Validar contraseña si se está cambiando
                is_valid, message = validate_password_strength(value)
                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=message
                    )
                setattr(user, "hashed_password", get_password_hash(value))
            elif field == "is_admin":
                # Actualizar tanto is_admin como rol
                setattr(user, "is_admin", value)
                setattr(user, "rol", "ADMIN" if value else "USER")
            else:
                setattr(user, field, value)

        db.commit()
        db.refresh(user)

        return user

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error actualizando usuario: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Eliminar usuario (solo ADMIN)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403, detail="Solo administradores pueden eliminar usuarios"
        )
    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # No permitir eliminar el último admin
        if user.is_admin:
            admin_count = db.query(User).filter(User.is_admin).count()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="No se puede eliminar el último administrador",
                )

        db.delete(user)
        db.commit()

        return {"message": "Usuario eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error eliminando usuario: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
