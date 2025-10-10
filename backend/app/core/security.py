# backend/app/core/security.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from pydantic import ValidationError

from app.core.constants import Roles, PERMISOS


# Configuración de hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hashear contraseña"""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any],
    secret_key: str,
    algorithm: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Crear token de acceso JWT"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    secret_key: str,
    algorithm: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Crear refresh token JWT"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    
    return encoded_jwt


def decode_token(token: str, secret_key: str, algorithm: str) -> Dict[str, Any]:
    """Decodificar token JWT"""
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo validar el token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_token_type(payload: Dict[str, Any], expected_type: str) -> None:
    """Verificar tipo de token"""
    token_type = payload.get("type")
    if token_type != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido. Se esperaba tipo '{expected_type}'",
            headers={"WWW-Authenticate": "Bearer"},
        )


def check_permission(user_role: str, required_permission: str) -> bool:
    """
    Verificar si un rol tiene un permiso específico
    
    Args:
        user_role: Rol del usuario (Roles enum)
        required_permission: Permiso requerido en formato "modulo.accion"
        
    Returns:
        bool: True si tiene permiso, False si no
        
    Examples:
        check_permission("ADMIN", "clientes.create") -> True
        check_permission("ASESOR", "usuarios.delete") -> False
    """
    if user_role not in PERMISOS:
        return False
    
    user_permissions = PERMISOS[user_role]
    
    # Verificar permiso exacto
    if required_permission in user_permissions:
        return True
    
    # Verificar permiso con wildcard (ej: "clientes.*")
    module = required_permission.split(".")[0]
    wildcard = f"{module}.*"
    
    return wildcard in user_permissions


def validate_password_strength(password: str) -> None:
    """
    Validar fortaleza de contraseña
    
    Requisitos:
    - Mínimo 8 caracteres
    - Al menos una mayúscula
    - Al menos una minúscula
    - Al menos un número
    """
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 8 caracteres"
        )
    
    if not any(c.isupper() for c in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe contener al menos una mayúscula"
        )
    
    if not any(c.islower() for c in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe contener al menos una minúscula"
        )
    
    if not any(c.isdigit() for c in password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe contener al menos un número"
        )
