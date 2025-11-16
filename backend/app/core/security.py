"""
Módulo de seguridad para autenticación JWT
Maneja creación, validación y decodificación de tokens
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

import jwt
from passlib.context import CryptContext

# Importar configuración centralizada
from app.core.config import settings

# Usar configuración centralizada desde settings
# SECRET_KEY ahora se obtiene de settings (validado y generado automáticamente en desarrollo)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 240  # 4 horas (Access Token) - se usa desde settings
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7 días (Refresh Token) - se usa desde settings

# Contexto para hashing de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica una contraseña contra su hash

    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Hash de la contraseña

    Returns:
        True si la contraseña es correcta, False en caso contrario
    """
    return bool(pwd_context.verify(plain_password, hashed_password))  # type: ignore[no-any-return]


def get_password_hash(password: str) -> str:
    """
    Genera un hash de una contraseña

    Args:
        password: Contraseña en texto plano

    Returns:
        Hash de la contraseña
    """
    return str(pwd_context.hash(password))  # type: ignore[no-any-return]


def create_access_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Crea un token de acceso JWT

    Args:
        subject: ID del usuario (subject del token)
        expires_delta: Tiempo de expiración personalizado
        additional_claims: Claims adicionales para el token

    Returns:
        Token JWT codificado
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}

    # Añadir claims adicionales si existen
    if additional_claims:
        to_encode.update(additional_claims)

    # Verificar que SECRET_KEY esté configurado (debería estar validado por validate_all())
    if not settings.SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY no está configurado. "
            "Configure SECRET_KEY como variable de entorno o ejecute validate_all() primero."
        )
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, int]) -> str:
    """
    Crea un token de refresh JWT

    Args:
        subject: ID del usuario

    Returns:
        Token de refresh JWT codificado
    """
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    # Verificar que SECRET_KEY esté configurado (debería estar validado por validate_all())
    if not settings.SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY no está configurado. "
            "Configure SECRET_KEY como variable de entorno o ejecute validate_all() primero."
        )
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodifica y valida un token JWT

    Args:
        token: Token JWT a decodificar

    Returns:
        Payload del token decodificado

    Raises:
        Exception: Si el token es inválido o expiró
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return dict(payload)  # type: ignore[no-any-return]
    except jwt.ExpiredSignatureError as e:
        # Token expirado
        raise Exception(f"Token expirado: {str(e)}")
    except jwt.InvalidTokenError as e:
        # Token inválido (firma incorrecta, formato incorrecto, etc.)
        raise Exception(f"Token inválido: {str(e)}")
    except Exception as e:
        # Cualquier otro error
        raise Exception(f"Error decodificando token: {str(e)}")


def verify_token_type(token: str, expected_type: str) -> bool:
    """
    Verifica que un token sea del tipo esperado

    Args:
        token: Token JWT
        expected_type: Tipo esperado ("access" o "refresh")

    Returns:
        True si el token es del tipo esperado, False en caso contrario
    """
    try:
        payload = decode_token(token)
        return payload.get("type") == expected_type
    except Exception:
        return False


def get_token_subject(token: str) -> Optional[str]:
    """
    Obtiene el subject (ID del usuario) de un token

    Args:
        token: Token JWT

    Returns:
        ID del usuario o None si el token es inválido
    """
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except Exception:
        return None


def is_token_expired(token: str) -> bool:
    """
    Verifica si un token ha expirado

    Args:
        token: Token JWT

    Returns:
        True si el token ha expirado, False en caso contrario
    """
    try:
        payload = decode_token(token)
        exp = payload.get("exp")
        if exp:
            return datetime.utcnow() > datetime.fromtimestamp(exp)
        return True
    except Exception:
        return True


def create_token_pair(subject: Union[str, int]) -> Dict[str, str]:
    """
    Crea un par de tokens (access + refresh)

    Args:
        subject: ID del usuario

    Returns:
        Diccionario con access_token y refresh_token
    """
    return {
        "access_token": create_access_token(subject),
        "refresh_token": create_refresh_token(subject),
    }
