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


def _validar_permisos_actualizacion(current_user: User, user_id: int):
    """Valida que el usuario tenga permisos para actualizar"""
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para actualizar este usuario",
        )


def _validar_email_unico(db: Session, email: str, user_id: int):
    """Valida que el email no esté registrado por otro usuario"""
    existing_user = db.query(User).filter(User.email == email, User.id != user_id).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado por otro usuario",
        )


def _actualizar_password(user, password: str):
    """Actualiza la contraseña del usuario"""
    is_valid, message = validate_password_strength(password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    setattr(user, "hashed_password", get_password_hash(password))


def _actualizar_is_admin(user, value: bool):
    """Actualiza is_admin y rol relacionado"""
    setattr(user, "is_admin", value)
    nuevo_rol = "ADMIN" if value else "USER"
    setattr(user, "rol", nuevo_rol)
    logger.debug(f"Actualizado is_admin={value}, rol={nuevo_rol}")


def _actualizar_campo_simple(user, field: str, value):
    """Actualiza un campo simple del usuario"""
    if field == "email" and value:
        value = value.lower().strip()

    try:
        setattr(user, field, value)
        logger.debug(f"Campo '{field}' actualizado correctamente")
    except Exception as field_error:
        logger.error(f"Error actualizando campo '{field}': {field_error}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al actualizar campo '{field}': {str(field_error)}",
        )


def _aplicar_actualizaciones(user, update_data: dict):
    """Aplica todas las actualizaciones a un usuario"""
    CAMPOS_VALIDOS = ["email", "nombre", "apellido", "cargo", "is_active"]
    CAMPOS_ESPECIALES = ["password", "is_admin", "rol"]

    for field, value in update_data.items():
        # Manejar campos especiales primero (no necesitan existir en el modelo)
        if field == "password" and value:
            _actualizar_password(user, value)
            continue
        elif field == "is_admin":
            _actualizar_is_admin(user, value)
            continue
        elif field == "rol":
            logger.debug("Campo 'rol' ignorado, se maneja con is_admin")
            continue

        # Verificar que el campo exista en el modelo para campos normales
        if not hasattr(user, field):
            logger.warning(f"Campo '{field}' no existe en el modelo User, omitiendo...")
            continue

        # Aplicar actualización para campos válidos
        if field in CAMPOS_VALIDOS:
            _actualizar_campo_simple(user, field, value)
        else:
            logger.warning(f"Campo '{field}' no se puede actualizar directamente, omitiendo...")
            continue


def _manejar_error_commit(commit_error: Exception, user_id: int):
    """Maneja errores durante el commit"""
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


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar usuario"""
    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        _validar_permisos_actualizacion(current_user, user_id)

        update_data = user_data.model_dump(exclude_unset=True)
        
        # Verificar que hay datos para actualizar
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se proporcionaron datos para actualizar"
            )

        if "email" in update_data and update_data["email"] != user.email:
            _validar_email_unico(db, update_data["email"], user_id)

        logger.info(f"Actualizando usuario {user_id} con campos: {list(update_data.keys())}")
        
        # Guardar valores anteriores para logging
        valores_anteriores = {
            'email': user.email,
            'nombre': user.nombre,
            'apellido': user.apellido,
            'is_admin': user.is_admin,
            'is_active': user.is_active,
        }
        
        _aplicar_actualizaciones(user, update_data)

        try:
            # Flush para asegurar que los cambios se apliquen antes del commit
            db.flush()
            db.commit()
            db.refresh(user)
            
            # Verificar que los cambios se aplicaron
            cambios_aplicados = []
            for campo in update_data.keys():
                if campo in valores_anteriores:
                    valor_anterior = valores_anteriores.get(campo)
                    valor_nuevo = getattr(user, campo, None)
                    if valor_anterior != valor_nuevo:
                        cambios_aplicados.append(f"{campo}: {valor_anterior} -> {valor_nuevo}")
            
            logger.info(
                f"Usuario {user_id} actualizado exitosamente - "
                f"Campos enviados: {list(update_data.keys())}, "
                f"Cambios aplicados: {cambios_aplicados if cambios_aplicados else 'ninguno (valores iguales)'}"
            )
        except Exception as commit_error:
            db.rollback()
            logger.error(
                f"Error en commit al actualizar usuario {user_id}: {commit_error}",
                exc_info=True,
            )
            _manejar_error_commit(commit_error, user_id)

        return user

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        error_detail = f"Error actualizando usuario: {str(e)}"
        logger.error(error_detail, exc_info=True)
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
