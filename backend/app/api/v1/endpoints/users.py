import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions_simple import Permission, has_permission
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
    # Crear un nuevo usuario (verificar permiso)
    if not has_permission(bool(current_user.is_admin), Permission.USER_CREATE):
        raise HTTPException(status_code=403, detail="No tienes permisos para crear usuarios")
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
    password_length = len(user_data.password) if user_data.password else 0
    logger.info(
        f"Creando usuario: email={user_data.email}, " f"password length={password_length}, is_admin={user_data.is_admin}"
    )
    is_valid, message = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    # Crear usuario
    # El ENUM en la BD solo acepta 'ADMIN'
    # El control de acceso real se hace con is_admin=True/False

    new_user = User(
        email=user_data.email,
        nombre=user_data.nombre,
        apellido=user_data.apellido,
        rol="ADMIN",  # Valor único aceptado por el ENUM
        cargo=user_data.cargo,
        is_admin=user_data.is_admin,  # Control real de permisos
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
        # Verificar permiso para listar usuarios
        if not has_permission(bool(current_user.is_admin), Permission.USER_READ):
            raise HTTPException(status_code=403, detail="No tienes permisos para ver usuarios")

        users = db.query(User).offset(skip).limit(limit).all()
        total = db.query(User).count()

        return UserListResponse(items=users, total=total, page=skip // limit + 1, page_size=limit)

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

        # Verificar permiso para ver usuarios
        if not has_permission(bool(current_user.is_admin), Permission.USER_READ):
            # Si no tiene permiso general, solo puede verse a sí mismo
            if current_user.id != user_id:
                raise HTTPException(status_code=403, detail="No tienes permisos para ver este usuario")

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

        # Validar email único si se está actualizando
        update_data = user_data.model_dump(exclude_unset=True)
        if "email" in update_data and update_data["email"] != user.email:
            existing_user = db.query(User).filter(User.email == update_data["email"], User.id != user_id).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El email ya está registrado por otro usuario",
                )

        logger.info(f"Actualizando usuario {user_id} con campos: {list(update_data.keys())}")

        for field, value in update_data.items():
            # Verificar que el campo existe en el modelo User
            if not hasattr(user, field):
                logger.warning(f"Campo '{field}' no existe en el modelo User, omitiendo...")
                continue

            if field == "password" and value:
                # Validar contraseña si se está cambiando
                is_valid, message = validate_password_strength(value)
                if not is_valid:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
                setattr(user, "hashed_password", get_password_hash(value))
            elif field == "is_admin":
                # Actualizar tanto is_admin como rol
                setattr(user, "is_admin", value)
                # Actualizar rol según is_admin - solo valores válidos: ADMIN o USER
                nuevo_rol = "ADMIN" if value else "USER"
                setattr(user, "rol", nuevo_rol)
                logger.debug(f"Actualizado is_admin={value}, rol={nuevo_rol}")
            elif field == "rol":
                # Ignorar campo rol directamente, se maneja automáticamente con is_admin
                logger.debug("Campo 'rol' ignorado, se maneja con is_admin")
                continue
            elif field in ["email", "nombre", "apellido", "cargo", "is_active"]:
                # Campos válidos del modelo User que se pueden actualizar directamente
                try:
                    # Validación especial para email (ya validado arriba)
                    if field == "email" and value:
                        value = value.lower().strip()  # Normalizar email
                    setattr(user, field, value)
                    logger.debug(f"Campo '{field}' actualizado correctamente")
                except Exception as field_error:
                    logger.error(
                        f"Error actualizando campo '{field}': {field_error}",
                        exc_info=True,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Error al actualizar campo '{field}': {str(field_error)}",
                    )
            else:
                # Campo no reconocido - omitir con advertencia
                logger.warning(f"Campo '{field}' no se puede actualizar directamente, omitiendo...")
                continue

        # Intentar commit con manejo de errores de BD
        try:
            db.commit()
            db.refresh(user)
            logger.info(f"Usuario {user_id} actualizado exitosamente")
        except Exception as commit_error:
            db.rollback()
            logger.error(
                f"Error en commit al actualizar usuario {user_id}: {commit_error}",
                exc_info=True,
            )
            # Verificar si es un error de constraint (ej: email duplicado, rol inválido)
            error_str = str(commit_error).lower()
            if "unique constraint" in error_str or "duplicate" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El email ya está registrado por otro usuario",
                )
            elif "check constraint" in error_str or "invalid" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Error de validación: {str(commit_error)}",
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error al guardar cambios: {str(commit_error)}",
                )

        return user

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        error_detail = f"Error actualizando usuario: {str(e)}"
        logger.error(error_detail, exc_info=True)
        # Incluir más detalles en el error para debugging
        error_trace = traceback.format_exc()
        logger.error(f"Traceback completo:\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Eliminar usuario (solo ADMIN)
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar usuarios")
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
