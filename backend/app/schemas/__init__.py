# backend/app/schemas/__init__.py
from app.schemas.cliente import ClienteCreate, ClienteUpdate, ClienteResponse
from app.schemas.prestamo import PrestamoCreate, PrestamoUpdate, PrestamoResponse
from app.schemas.pago import PagoCreate, PagoResponse
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserProfile,
    Token,
    LoginRequest,
    RefreshTokenRequest
)

__all__ = [
    # Cliente
    "ClienteCreate",
    "ClienteUpdate",
    "ClienteResponse",
    # Préstamo
    "PrestamoCreate",
    "PrestamoUpdate",
    "PrestamoResponse",
    # Pago
    "PagoCreate",
    "PagoResponse",
    # Usuario
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserProfile",
    "Token",
    "LoginRequest",
    "RefreshTokenRequest",
]
