# backend/app/api/deps.py
"""
Dependencias comunes para los endpoints
Incluye autenticación, permisos, y paginación
"""
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import decode_token
from app.core.permissions import UserRole, Permission, has_permission
from app.models.user import User
from app.schemas.auth import TokenPayload


# Security scheme para JWT
security = HTTPBearer()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Obtiene el usuario actual desde el token JWT
    
    Args:
        db: Sesión de base de datos
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
    
    try:
        token = credentials.credentials
        payload = decode_token(token)
        
        # Verificar que sea un access token
        if payload.get("type") != "access":
            raise credentials_exception
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Buscar usuario en BD
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    return current_user


def require_role(*allowed_roles: UserRole):
    """
    Dependency para requerir uno o más roles específicos
    
    Args:
        allowed_roles: Roles permitidos
        
    Returns:
        Función de dependencia
        
    Usage:
        @app.get("/admin", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.rol not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol requerido: {', '.join(r.value for r in allowed_roles)}"
            )
        return current_user
    return role_checker


def require_permission(*required_permissions: Permission):
    """
    Dependency para requerir uno o más permisos específicos
    
    Args:
        required_permissions: Permisos requeridos
        
    Returns:
        Función de dependencia
        
    Usage:
        @app.post("/clientes", dependencies=[Depends(require_permission(Permission.CLIENTE_CREATE))])
    """
    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        user_role = UserRole(current_user.rol)
        
        # Verificar cada permiso requerido
        for perm in required_permissions:
            if not has_permission(user_role, perm):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permiso requerido: {perm.value}"
                )
        
        return current_user
    return permission_checker


def get_admin_user(
    current_user: User = Depends(require_role(UserRole.ADMIN))
) -> User:
    """
    Dependency para endpoints que requieren rol ADMIN
    
    Returns:
        Usuario con rol ADMIN
    """
    return current_user


# Dependency para paginación
class PaginationParams:
    """Parámetros de paginación comunes"""
    
    def __init__(
        self,
        page: int = 1,
        page_size: int = 10,
        skip: Optional[int] = None,
        limit: Optional[int] = None
    ):
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


def get_pagination_params(
    page: int = 1,
    page_size: int = 10
) -> PaginationParams:
    """
    Dependency para obtener parámetros de paginación
    
    Args:
        page: Número de página (default: 1)
        page_size: Tamaño de página (default: 10, max: 100)
        
    Returns:
        Parámetros de paginación
        
    Usage:
        @app.get("/items")
        def get_items(pagination: PaginationParams = Depends(get_pagination_params)):
            skip = pagination.skip
            limit = pagination.limit
    """
    return PaginationParams(page=page, page_size=page_size)
