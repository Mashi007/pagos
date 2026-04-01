"""
Seguridad: JWT y contraseñas (auth)
"""
from datetime import datetime, timedelta
from typing import Any, Optional

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(
    subject: str | int,
    extra: Optional[dict] = None,
    expire_minutes: Optional[int] = None,
) -> str:
    minutes = (
        expire_minutes
        if expire_minutes is not None
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    expire = datetime.utcnow() + timedelta(minutes=minutes)
    to_encode: dict[str, Any] = {"sub": str(subject), "exp": expire, "type": "access"}
    if extra:
        to_encode.update(extra)
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | int, expire_days: Optional[int] = None) -> str:
    days = (
        expire_days
        if expire_days is not None
        else settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    expire = datetime.utcnow() + timedelta(days=days)
    to_encode = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None

def create_recibo_token(cedula: str, expire_hours: int = 2) -> str:
    """Token para descarga de recibo desde estado de cuenta (sin login). Cedula sin guion."""
    expire = datetime.utcnow() + timedelta(hours=expire_hours)
    to_encode = {"sub": cedula, "exp": expire, "type": "recibo"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_cobros_public_token(cedula_normalized: str, expire_minutes: int = 120) -> str:
    """JWT de sesion para reporte de pago publico tras verificar OTP al correo registrado."""
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    to_encode: dict[str, Any] = {
        "sub": cedula_normalized.replace("-", ""),
        "exp": expire,
        "type": "cobros_public",
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_recibo_infopagos_token(pago_id: int, expire_hours: int = 2) -> str:
    """Token de un solo uso para que el colaborador descargue el recibo tras registrar pago por Infopagos."""
    expire = datetime.utcnow() + timedelta(hours=expire_hours)
    to_encode = {"sub": str(pago_id), "pago_id": pago_id, "exp": expire, "type": "recibo_infopagos"}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
