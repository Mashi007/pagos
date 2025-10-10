# backend/app/schemas/__init__.py
"""
Schemas centralizados para la API.
Actualizado: Eliminadas importaciones no existentes en user.py
"""

from app.schemas.cliente import ClienteCreate, ClienteUpdate, ClienteResponse
from app.schemas.prestamo import PrestamoCreate, PrestamoUpdate, PrestamoResponse
from app.schemas.pago import PagoCreate, PagoResponse

# Importaciones de user - SOLO las que existen realmente
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    Token,
    LoginRequest,
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
    
    # Usuario y Autenticación
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "Token",
    "LoginRequest",
]
