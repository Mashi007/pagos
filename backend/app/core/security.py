"""
Sistema de seguridad: JWT, hashing de passwords, tokens y dependencias de Fa...
"""

from datetime import datetime, timedelta
from typing import Any, Optional

import jwt
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from passlib.context import CryptContext

from app.core.config import settings

# Constantes de seguridad
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 7
MIN_PASSWORD_LENGTH = 8
PASSWORD_RESET_EXPIRE_HOURS = 1

# Configuración de hashing de passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configuración JWT

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS

# Esquema OAuth2 para FastAPI, que define dónde esperar el token
# (Authorization: Bearer <token>)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con el hash
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Genera un hash de una contraseña
    """
    return pwd_context.hash(password)


def create_access_token(
    subject: str | int,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None,
) -> str:
    """
    Crea un token de acceso JWT
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}

    # Añadir claims adicionales si existen
    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(subject: str | int) -> str:
    """
    Crea un token de refresh JWT
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    Decodifica y valida un token JWT

    Raises:
        PyJWTError: Si el token es inválido o expiró
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        return payload
    except PyJWTError as e:
        # Re-lanza PyJWTError para que el manejador de excepciones de FastAPI
        # lo capture
        raise PyJWTError(f"Error decodificando token: {str(e)}")


# -------------------------------------------------------------
# DEPENDENCIAS DE AUTENTICACIÓN PARA FASTAPI (ELIMINADAS - DUPLICADAS)
# -------------------------------------------------------------
# Las funciones get_current_user y get_current_active_user están definidas e...
# para evitar duplicación y conflictos de importación

# -------------------------------------------------------------
# [Resto de funciones originales]
# -------------------------------------------------------------


def verify_token_type(token: str, expected_type: str) -> bool:
    """
    Verifica que el token sea del tipo esperado (access o refresh)
    """
    try:
        payload = decode_token(token)
        return payload.get("type") == expected_type
    except PyJWTError:
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Valida la fortaleza de una contraseña
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, "La contraseña debe tener al menos 8 caracteres"

    if not any(c.isupper() for c in password):
        return False, "La contraseña debe contener al menos una mayúscula"

    if not any(c.islower() for c in password):
        return False, "La contraseña debe contener al menos una minúscula"

    if not any(c.isdigit() for c in password):
        return False, "La contraseña debe contener al menos un número"

    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        return (
            False,
            "La contraseña debe contener al menos un carácter especial",
        )

    return True, "Contraseña válida"


def generate_password_reset_token(email: str) -> str:
    """
    Genera un token para reset de contraseña
    """
    expire = datetime.utcnow() + timedelta(
        hours=PASSWORD_RESET_EXPIRE_HOURS
    )  # Expira en 1 hora

    to_encode = {"exp": expire, "sub": email, "type": "password_reset"}

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=ALGORITHM
    )
    return encoded_jwt


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    Verifica un token de reset de contraseña y retorna el email
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "password_reset":
            return None
        return payload.get("sub")
    except PyJWTError:
        return None
