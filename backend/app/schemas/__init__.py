# backend/app/schemas/__init__.py
"""
Schemas centralizados para la API.
Actualizado: Sincronizado con schemas existentes en user.py
"""

from app.schemas.cliente import ClienteCreate, ClienteUpdate, ClienteResponse
from app.schemas.prestamo import PrestamoCreate, PrestamoUpdate, PrestamoResponse
from app.schemas.pago import PagoCreate, PagoResponse

# Importaciones de user - Schemas base de usuario
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
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
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserListResponse",
]
