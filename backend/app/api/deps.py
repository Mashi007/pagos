# backend/app/api/deps.py
from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import decode_token, verify_token_type
from app.core.constants import EstadoUsuario
from app.config import settings


# Security scheme
security = HTTPBearer()


def get_db() -> Generator:
    """Dependency para obtener sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Obtener usuario actual desde JWT token
    
    Dependencia para proteger endpoints que requieren autenticación
    """
    token = credentials.credentials
    
    # Decodificar token
    payload = decode_token(token, settings.SECRET_KEY, settings.ALGORITHM)
    
    # Verificar que sea access token
    verify_token_type(payload, "access")
    
    # Obtener user_id
    user_id: int = int(payload.get("sub"))
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo validar el token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Obtener usuario de BD
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Verificar que esté activo
    if user.estado != EstadoUsuario.ACTIVO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Usuario {user.estado.value}"
        )
    
    # Verificar si está bloqueado
    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Usuario bloqueado hasta {user.bloqueado_hasta}"
        )
    
    return user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Verificar que el usuario actual sea superusuario
    
    Dependencia para endpoints que solo superusers pueden acceder
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos de superusuario"
        )
    return current_user
