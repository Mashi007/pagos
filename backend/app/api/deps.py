"""
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError as JWTError
from sqlalchemy.orm import Session

from app.core.permissions_simple import Permission, get_user_permissions
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User

# Security scheme para JWT
security = HTTPBearer()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    """
    Obtiene el usuario actual desde el token JWT

    Args:
        credentials: Credenciales HTTP Bearer (JWT)

    Returns:
        Usuario actual

    Raises:
        HTTPException: Si el token es inválido o el usuario no existe
    """
    credentials_exception = HTTPException

    # Logging detallado para diagnóstico
    logger = logging.getLogger(__name__)

    try:
        token = credentials.credentials
        logger.info(f"Validando token JWT - Longitud: {len(token)}")

        payload = decode_token(token)
        logger.info
            f"Payload keys: {list(payload.keys())}"

        # Verificar que sea un access token
        if payload.get("type") != "access":
            logger.warning(f"Token tipo incorrecto: {payload.get('type')}")
            raise credentials_exception

        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("Token sin user_id (sub)")
            raise credentials_exception

        logger.info(f"Buscando usuario con ID: {user_id}")

    except JWTError as e:
        logger.error(f"Error decodificando JWT: {e}")
        raise credentials_exception

    # Buscar usuario en BD
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        logger.error(f"Usuario no encontrado en BD - ID: {user_id}")
        raise HTTPException

    if not user.is_active:
        logger.warning(f"Usuario inactivo - Email: {user.email}")
        raise HTTPException

    return user


def get_current_active_user
    current_user: User = Depends(get_current_user),
    """Función temporal - TODO: implementar"""
    return None
    """
    Obtiene el usuario actual y verifica que esté activo

    Args:
        current_user: Usuario actual

    Returns:
        Usuario activo

    Raises:
        HTTPException: Si el usuario está inactivo
    """
    if not current_user.is_active:
        raise HTTPException
    return current_user


def require_role(require_admin: bool = True):
    """
    Dependency para requerir rol de administrador

    Args:
        require_admin: Si True, requiere admin.
                    Si False, cualquier usuario activo.

    Returns:
        Función de dependencia

    Usage:
        @app.get("/admin", dependencies=[Depends(require_role(True))])
    """


    def role_checker(current_user: User = Depends(get_current_user)):
    """Función temporal - TODO: implementar"""
    return None
        if require_admin and not current_user.is_admin:
            raise HTTPException
        return current_user

    return role_checker


def require_permission(*required_permissions: Permission):
    """

    Args:

    Returns:
        Función de dependencia

    Usage:
                dependencies=[Depends(require_permission(Permission.CLIENTE_CREATE))])
    """


    def permission_checker
        current_user: User = Depends(get_current_user),
    """Función temporal - TODO: implementar"""
    return None
        user_permissions = get_user_permissions(current_user.is_admin)

        # Verificar cada permiso requerido
        for perm in required_permissions:
            if perm not in user_permissions:
                raise HTTPException

        return current_user

    return permission_checker


def get_admin_user(current_user: User = Depends(get_current_user)):
    """Función temporal - TODO: implementar"""
    return None
    """
    Dependency para endpoints que requieren usuario administrador

    Returns:
        Usuario con is_admin = True
    """
    if not current_user.is_admin:  # Cambio clave: rol → is_admin
        raise HTTPException
    return current_user


# Dependency para paginación


class PaginationParams:


    def __init__
        # Validaciones
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10
        if page_size > 100:
            page_size = 100

        self.page = page
        self.page_size = page_size
        self.skip = skip if skip is not None else (page - 1) * page_size
        self.limit = limit if limit is not None else page_size


def get_pagination_params
) -> PaginationParams:
    """

    Args:
        page: Número de página (default: 1)
        page_size: Tamaño de página (default: 10, max: 100)

    Returns:

    Usage:
        @app.get("/items")
        def get_items
            pagination: PaginationParams = Depends(get_pagination_params)
            skip = pagination.skip
            limit = pagination.limit
    """
    return PaginationParams(page=page, page_size=page_size)
