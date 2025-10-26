"""
Dependencias de la API
Funciones de dependencia para autenticación y autorización
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
):
    """
    Obtiene el usuario actual desde el token JWT

    Args:
        credentials: Credenciales HTTP Bearer (JWT)

    Returns:
        Usuario actual

    Raises:
        HTTPException: Si el token es inválido o el usuario no existe
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Logging detallado para diagnóstico
    logger = logging.getLogger(__name__)

    try:
        token = credentials.credentials
        logger.info(f"Validando token JWT - Longitud: {len(token)}")

        payload = decode_token(token)
        logger.info(f"Payload keys: {list(payload.keys())}")

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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")

    if not user.is_active:
        logger.warning(f"Usuario inactivo - Email: {user.email}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
):
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")
    return current_user


def get_current_user_with_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Obtiene el usuario actual con sus permisos

    Args:
        current_user: Usuario actual
        db: Sesión de base de datos

    Returns:
        Usuario con permisos
    """
    permissions = get_user_permissions(db, current_user.id)
    current_user.permissions = permissions
    return current_user


def require_permission(permission: Permission):
    """
    Decorador para requerir un permiso específico

    Args:
        permission: Permiso requerido

    Returns:
        Función de dependencia
    """

    def permission_dependency(
        current_user: User = Depends(get_current_user_with_permissions),
    ):
        if permission not in current_user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso requerido: {permission.value}",
            )
        return current_user

    return permission_dependency


def get_optional_current_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
):
    """
    Obtiene el usuario actual si está autenticado, sino retorna None

    Args:
        credentials: Credenciales opcionales

    Returns:
        Usuario actual o None
    """
    if not credentials:
        return None

    try:
        return get_current_user(db, credentials)
    except HTTPException:
        return None
