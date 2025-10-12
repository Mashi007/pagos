# backend/app/core/security.py
"""
Sistema de seguridad: JWT, hashing de passwords, tokens
"""
from datetime import datetime, timedelta
from typing import Optional, Any
from jose import JWTError, jwt
from passlib.context import CryptContext

# ✅ CORREGIDO: Importar desde app.core.config
from app.core.config import get_settings

settings = get_settings()

# Configuración de hashing de passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con el hash
    
    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Hash de la contraseña almacenada
        
    Returns:
        True si coinciden, False si no
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Genera un hash de una contraseña
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        Hash de la contraseña
    """
    return pwd_context.hash(password)


def create_access_token(
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None
) -> str:
    """
    Crea un token de acceso JWT
    
    Args:
        subject: ID del usuario o email
        expires_delta: Tiempo de expiración personalizado
        additional_claims: Claims adicionales (rol, permisos, etc.)
        
    Returns:
        Token JWT codificado
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "access"
    }
    
    # Añadir claims adicionales si existen
    if additional_claims:
        to_encode.update(additional_claims)
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str | int) -> str:
    """
    Crea un token de refresh JWT
    
    Args:
        subject: ID del usuario
        
    Returns:
        Refresh token JWT codificado
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "type": "refresh"
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decodifica y valida un token JWT
    
    Args:
        token: Token JWT a decodificar
        
    Returns:
        Payload del token decodificado
        
    Raises:
        JWTError: Si el token es inválido o expiró
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise JWTError(f"Error decodificando token: {str(e)}")


def verify_token_type(token: str, expected_type: str) -> bool:
    """
    Verifica que el token sea del tipo esperado (access o refresh)
    
    Args:
        token: Token JWT
        expected_type: Tipo esperado ("access" o "refresh")
        
    Returns:
        True si el tipo coincide
    """
    try:
        payload = decode_token(token)
        return payload.get("type") == expected_type
    except JWTError:
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Valida la fortaleza de una contraseña
    
    Requisitos:
    - Mínimo 8 caracteres
    - Al menos una mayúscula
    - Al menos una minúscula
    - Al menos un número
    - Al menos un carácter especial
    
    Args:
        password: Contraseña a validar
        
    Returns:
        (is_valid, message)
    """
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    
    if not any(c.isupper() for c in password):
        return False, "La contraseña debe contener al menos una mayúscula"
    
    if not any(c.islower() for c in password):
        return False, "La contraseña debe contener al menos una minúscula"
    
    if not any(c.isdigit() for c in password):
        return False, "La contraseña debe contener al menos un número"
    
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return False, "La contraseña debe contener al menos un carácter especial"
    
    return True, "Contraseña válida"


def generate_password_reset_token(email: str) -> str:
    """
    Genera un token para reset de contraseña
    
    Args:
        email: Email del usuario
        
    Returns:
        Token JWT para reset de contraseña
    """
    expire = datetime.utcnow() + timedelta(hours=1)  # Expira en 1 hora
    
    to_encode = {
        "exp": expire,
        "sub": email,
        "type": "password_reset"
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verifica un token de reset de contraseña y retorna el email
    
    Args:
        token: Token de reset
        
    Returns:
        Email del usuario si el token es válido, None si no
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "password_reset":
            return None
        return payload.get("sub")
    except JWTError:
        return None
